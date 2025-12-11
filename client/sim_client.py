from scapy.all import *
import random
import argparse

def generate_dhcp_request(interface, server_ip, option82_val):
    print(f"Generating DHCP Request on {interface} to {server_ip}")
    
    # Generate random MAC
    mac_raw = [random.randint(0x00, 0xff) for _ in range(6)]
    mac_str = ":".join(map(lambda x: "%02x" % x, mac_raw))
    print(f"Client MAC: {mac_str}")
    
    # Unique transaction ID
    xid = random.randint(0, 0xFFFFFFFF)

    # Base DHCP Options
    dhcp_mtype = ('message-type', 'discover')
    dhcp_params = ('param_req_list', [1, 3, 6, 15, 26, 28, 51, 58, 59])
    dhcp_end = ('end')
    
    options = [dhcp_mtype, dhcp_params]

    # Add Option 82 if specified (Simulated Agent Information)
    if option82_val:
        # Option 82 structure: suboptions (1: Circuit ID, 2: Remote ID)
        # We'll just put the raw string into suboption 1 for simplicity or
        # construct a structured one if needed. Scapy handles some structure but
        # 'relay_agent_Information' expects usually bytes or structured subopts.
        
        # Simple string-based Option 82 for now
        # sub-opt 1 (Circuit ID) = option82_val
        circuit_id = bytes(option82_val, 'utf-8')
        opt82_data = b'\x01' + bytes([len(circuit_id)]) + circuit_id
        
        print(f"Adding Option 82 (Circuit ID): {option82_val}")
        options.append(('relay_agent_information', opt82_data))

    options.append(dhcp_end)

    # Construct Packet
    # Note: src='0.0.0.0' for DHCP Discover usually, but we need to send it out.
    # scapy will handle routing if we use 'sendp' on layer 2 or 'send' on layer 3.
    # We use BOOTP/DHCP structure.
    
    ether = Ether(dst="ff:ff:ff:ff:ff:ff", src=mac_str)
    ip = IP(src="0.0.0.0", dst="255.255.255.255")
    udp = UDP(sport=68, dport=67)
    bootp = BOOTP(chaddr=bytes(mac_raw), xid=xid, flags=0x8000) # Broadcast flag
    dhcp = DHCP(options=options)
    
    packet = ether / ip / udp / bootp / dhcp
    
    # Send packet
    print("Sending packet...")
    sendp(packet, iface=interface, verbose=True)
    print("Packet sent.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simulate DHCP Request with Option 82')
    parser.add_argument('--interface', '-i', type=str, default='dhcp', help='Network interface to use')
    parser.add_argument('--server', '-s', type=str, default='255.255.255.255', help='DHCP Server IP (or broadcast)')
    parser.add_argument('--opt82', '-o', type=str, help='Value for Option 82 (Circuit-ID)')
    
    args = parser.parse_args()
    
    generate_dhcp_request(args.interface, args.server, args.opt82)
