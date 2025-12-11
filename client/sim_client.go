package main

import (
	"flag"
	"fmt"
	"log"
	"net"
	"time"

	"github.com/insomniacslk/dhcp/dhcpv4"
	"github.com/insomniacslk/dhcp/dhcpv4/client4"
)

func main() {
	ifaceName := flag.String("i", "dhcp", "Interface to use")
	option82Val := flag.String("o", "", "Option 82 value (e.g. OLT_TEST)")
	flag.Parse()

	log.Printf("Starting DHCP Simulation on %s", *ifaceName)

	// Open raw socket on interface
	client, err := client4.NewClient()
	if err != nil {
		log.Fatal(err)
	}
	defer client.Close()

	// Wait for interface to be up/ready
	time.Sleep(500 * time.Millisecond)

	// --- 1. DISCOVER ---
	modifiers := []dhcpv4.Modifier{
		dhcpv4.WithOption(dhcpv4.OptRelayAgentInfo(
			dhcpv4.OptGeneric(dhcpv4.AgentCircuitIDSubOption, []byte(*option82Val)),
		)),
	}

	conversation, err := client.Exchange(*ifaceName, modifiers...)
	if err != nil {
		log.Fatalf("DHCP Exchange failed: %v", err)
	}

	for _, packet := range conversation {
		log.Printf("Received %s", packet.MessageType())
		log.Printf("  Your IP: %v", packet.YourIPAddr)
		log.Printf("  Server IP: %v", packet.ServerIPAddr)
        
        // Print Summary
        if packet.MessageType() == dhcpv4.MessageTypeAck {
            log.Printf("SUCCESS! Lease acquired: %s", packet.YourIPAddr)
        }
	}
}
