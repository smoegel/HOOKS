from scapy.all import *
import random
import argparse

conf.checkIPaddr = False # Disable IP address matching (since we use 0.0.0.0)

def get_option(dhcp_options, key):
    """Note: scapy options are lists of tuples or plain values"""
    for item in dhcp_options:
        if isinstance(item, tuple) and item[0] == key:
            return item[1]
    return None

import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def sniff_dhcp_response(interface, match_xid, timeout=5):
    # Capture packets that match DHCP ports
    # We use a stop_filter to return immediately when we find OUR packet
    matched_packet = None
    
    def packet_callback(pkt):
        nonlocal matched_packet
        if BOOTP in pkt and pkt[BOOTP].xid == match_xid:
            matched_packet = pkt
            return True # Stop sniffing
        return False
    
    # Listen on specific interface to be sure
    sniff(iface=interface, 
          filter="udp and src port 67 and dst port 68", 
          prn=lambda p: log(f"Sniffed: {p.summary()}"), 
          stop_filter=packet_callback, 
          timeout=timeout,
          store=0) # Don't store all, just what we catch
          
    return matched_packet

def simulate_dhcp_transaction(interface, server_ip, option82_val):
    log(f"--- Starting DHCP Simulation using output interface {interface} ---")
    
    # Generate random MAC
    mac_raw = [random.randint(0x00, 0xff) for _ in range(6)]
    mac_str = ":".join(map(lambda x: "%02x" % x, mac_raw))
    log(f"Client MAC: {mac_str}")
    
    # Unique transaction ID
    xid = random.randint(0, 0xFFFFFFFF)

    # --- Step 1: DISCOVER ---
    log("\n[1] Sending DHCP DISCOVER...")
    
    dhcp_dis_opts = [
        ('message-type', 'discover'),
        ('param_req_list', [1, 3, 6, 15, 26, 28, 51, 58, 59]),
    ]
    
    if option82_val:
        circuit_id = bytes(option82_val, 'utf-8')
        opt82_data = b'\x01' + bytes([len(circuit_id)]) + circuit_id
        dhcp_dis_opts.append(('relay_agent_information', opt82_data))
        log(f"    (Attached Option 82: {option82_val})")

    dhcp_dis_opts.append('end')

    ether = Ether(dst="ff:ff:ff:ff:ff:ff", src=mac_str)
    ip = IP(src="0.0.0.0", dst="255.255.255.255")
    udp = UDP(sport=68, dport=67)
    bootp = BOOTP(chaddr=bytes(mac_raw), xid=xid, flags=0x8000) # Broadcast
    dhcp_discover = DHCP(options=dhcp_dis_opts)
    
    packet_discover = ether / ip / udp / bootp / dhcp_discover
    
    # Start thread for sniffing to avoid race condition (sniff needs to start before send)
    # Using AsyncSniffer again but with stop_filter logic
    
    sniffer = AsyncSniffer(iface=interface, 
                           filter="udp and src port 67 and dst port 68",
                           stop_filter=lambda p: BOOTP in p and p[BOOTP].xid == xid,
                           timeout=5)
    sniffer.start()
    
    # Give sniffer a fraction of a second to attach
    time.sleep(0.1)
    
    # Send packet
    sendp(packet_discover, iface=interface, verbose=0)
    
    # Wait for result
    sniffer.join(timeout=6)
    
    if not sniffer.results:
        log("!!! No DHCP OFFER received (matching XID). Timeout.")
        # Debug: check if any packets were seen? (AsyncSniffer stores results)
        return

    ans_offer = sniffer.results[0]
    log("    Received DHCP OFFER")
    
    offered_ip = ans_offer[BOOTP].yiaddr
    server_id_opt = get_option(ans_offer[DHCP].options, 'server_id')
    log(f"    Offered IP: {offered_ip}")
    log(f"    Server ID: {server_id_opt}")

    # --- Step 2: REQUEST ---
    log("\n[2] Sending DHCP REQUEST...")
    
    dhcp_req_opts = [
        ('message-type', 'request'),
        ('requested_addr', offered_ip),
        ('server_id', server_id_opt),
        ('param_req_list', [1, 3, 6, 15, 26, 28, 51, 58, 59]),
    ]
    
    if option82_val:
        circuit_id = bytes(option82_val, 'utf-8')
        opt82_data = b'\x01' + bytes([len(circuit_id)]) + circuit_id
        dhcp_req_opts.append(('relay_agent_information', opt82_data))

    dhcp_req_opts.append('end')

    bootp_req = BOOTP(chaddr=bytes(mac_raw), xid=xid, flags=0x8000)
    dhcp_request = DHCP(options=dhcp_req_opts)
    
    packet_request = ether / ip / udp / bootp_req / dhcp_request
    
    # Prepare sniffer for ACK
    sniffer_ack = AsyncSniffer(iface=interface, 
                           filter="udp and src port 67 and dst port 68",
                           stop_filter=lambda p: BOOTP in p and p[BOOTP].xid == xid,
                           timeout=5)
    sniffer_ack.start()
    time.sleep(0.1)

    # Send packet
    sendp(packet_request, iface=interface, verbose=0)
    
    # Wait for result
    sniffer_ack.join(timeout=6)
    
    if not sniffer_ack.results:
        log("!!! No DHCP ACK received. Timeout.")
        return
        
    ans_ack = sniffer_ack.results[0]
    
    msg_type = get_option(ans_ack[DHCP].options, 'message-type')
    
    if msg_type == 5: # ACK
        log(f"    Received DHCP ACK! IP {offered_ip} successfully leased.")
    elif msg_type == 6: # NAK
        log(f"    Received DHCP NAK. Request refused.")
    else:
        log(f"    Received unexpected message type: {msg_type}")

    log("\n--- Transaction Complete ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simulate DHCP Client (DORA) with Option 82')
    parser.add_argument('--interface', '-i', type=str, default='dhcp', help='Network interface to use')
    parser.add_argument('--server', '-s', type=str, default='255.255.255.255', help='DHCP Server IP (or broadcast)')
    parser.add_argument('--opt82', '-o', type=str, help='Value for Option 82 (Circuit-ID)')
    
    args = parser.parse_args()
    
    simulate_dhcp_transaction(args.interface, args.server, args.opt82)
