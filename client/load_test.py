#!/usr/bin/env python3
import sys
import time
import random
import argparse
import threading
import logging
from datetime import datetime
# Suppress Scapy warnings about unknown options
logging.getLogger("scapy").setLevel(logging.ERROR)
from scapy.all import *

# List of cities for Option 82
CITIES = [
    "Bratislava", "Kosice", "Presov", "Zilina", "Banska Bystrica", 
    "Nitra", "Trnava", "Trencin", "Martin", "Poprad", "Prievidza", 
    "Zvolen", "Povazska Bystrica", "Nove Zamky", "Michalovce"
]

# Track transactions
sent_xids = {}  # xid -> {mac, city, status}
lock = threading.Lock()
stop_sniffer = threading.Event()

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def random_mac():
    return "02:00:00:%02x:%02x:%02x" % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )

def mac_2_bytes(mac):
    return bytes.fromhex(mac.replace(":", ""))

def packet_callback(pkt):
    if DHCP in pkt:
        # Check message type
        msg_type = None
        for opt in pkt[DHCP].options:
            if opt[0] == "message-type":
                msg_type = opt[1]
                break
        
        xid = pkt[BOOTP].xid
        
        if msg_type == 2:  # OFFER
            with lock:
                if xid in sent_xids and sent_xids[xid]['status'] == 'DISCOVERED':
                    sent_xids[xid]['status'] = 'OFFERED'
                    # Extract Server ID and Offered IP for REQUEST
                    server_id = pkt[IP].src
                    offered_ip = pkt[BOOTP].yiaddr
                    
                    # Schedule sending REQUEST (in a separate thread to not block sniffer)
                    threading.Thread(target=send_request, args=(xid, server_id, offered_ip)).start()
        
        elif msg_type == 5: # ACK
            # print(f"  [Sniffer DEBUG] ACK received for XID {hex(xid)}")
            with lock:
                if xid in sent_xids:
                     sent_xids[xid]['status'] = 'ACKED'
                     # print(f"  [Sniffer] XID {hex(xid)} ACKED (IP: {pkt[BOOTP].yiaddr})")

def send_request(xid, server_id, offered_ip):
    with lock:
        if xid not in sent_xids:
            return
        mac = sent_xids[xid]['mac']
        city = sent_xids[xid]['city'] # Preserve city in Option 82 for Request too

    dhcp_request = (
        Ether(src=mac, dst="ff:ff:ff:ff:ff:ff") /
        IP(src="0.0.0.0", dst="255.255.255.255") /
        UDP(sport=68, dport=67) /
        BOOTP(chaddr=mac_2_bytes(mac), xid=xid) /
        DHCP(options=[("message-type", "request"),
                      ("server_id", server_id),
                      ("requested_addr", offered_ip),
                      ("relay_agent_Information", b"\x01\x08" + city.encode('utf-8')),
                      "end"])
    )
    
    try:
        conf.iface = "dhcp" # Ensure correct interface context for thread
        sendp(dhcp_request, iface="dhcp", verbose=0)
        with lock:
             if xid in sent_xids:
                sent_xids[xid]['status'] = 'REQUESTED'
    except Exception as e:
        print(f"Error sending request: {e}")

def load_test(interface, count, delay):
    print(f"[{get_timestamp()}] --- Starting DORA Load Test: {count} clients on {interface} ---")
    conf.iface = interface
    
    # Start background sniffer
    print(f"[{get_timestamp()}] [*] Starting sniffer...")
    sniffer = AsyncSniffer(iface=interface, filter="udp and port 68", prn=packet_callback, store=0, stop_filter=lambda x: stop_sniffer.is_set())
    sniffer.start()
    time.sleep(0.5)

    start_time = time.time()

    for i in range(count):
        mac = random_mac()
        xid = random.randint(1, 0xFFFFFFFF)
        city = random.choice(CITIES)
        
        # Store state
        with lock:
            sent_xids[xid] = {'mac': mac, 'city': city, 'status': 'DISCOVERED'}

        # Craft DISCOVER
        dhcp_discover = (
            Ether(src=mac, dst="ff:ff:ff:ff:ff:ff") /
            IP(src="0.0.0.0", dst="255.255.255.255") /
            UDP(sport=68, dport=67) /
            BOOTP(chaddr=mac_2_bytes(mac), xid=xid) /
            DHCP(options=[("message-type", "discover"), 
                          ("relay_agent_Information", b"\x01\x08" + city.encode('utf-8')), 
                          "end"])
        )

        try:
            sendp(dhcp_discover, iface=interface, verbose=0)
            if (i + 1) % 10 == 0:
                 print(f"[{get_timestamp()}] [{i+1}/{count}] D-O-R-A initiated ({city})")
        except Exception as e:
            print(f"[{get_timestamp()}] [{i+1}/{count}] Failed to send: {e}")
            
        time.sleep(delay)

    print(f"[{get_timestamp()}] --- Sending Complete. Waiting for full transactions (3s)... ---")
    time.sleep(3)
    stop_sniffer.set()
    sniffer.stop()

    total_duration = time.time() - start_time
    
    acked_count = sum(1 for v in sent_xids.values() if v['status'] == 'ACKED')
    
    req_per_sec = count / (total_duration - 3) # approx send duration
    actual_tps = acked_count / total_duration

    print(f"\n[{get_timestamp()}] --- Load Test Results ---")
    print(f"Clients Simulated: {count}")
    print(f"Fully ACKED Leases: {acked_count}")
    print(f"Effective TPS: {actual_tps:.2f} leases/sec")
    
    if count == acked_count:
        print("SUCCESS: 100% Lease Rate")
    else:
        loss = count - acked_count
        print(f"WARNING: {loss} failed transactions")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DHCP Load Tester")
    parser.add_argument("-i", "--interface", required=True, help="Interface to use")
    parser.add_argument("-n", "--count", type=int, default=50, help="Number of packets to send")
    parser.add_argument("-d", "--delay", type=float, default=0.1, help="Delay between packets (sec)")
    
    args = parser.parse_args()
    # Explicitly set global interface for thread safety in scapy
    conf.iface = args.interface
    load_test(args.interface, args.count, args.delay)
