package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"math/rand"
	"net"
	"sync"
	"time"

	"github.com/insomniacslk/dhcp/dhcpv4"
	"github.com/insomniacslk/dhcp/dhcpv4/nclient4"
)

var cities = []string{
	"Bratislava", "Kosice", "Presov", "Zilina", "Banska Bystrica",
	"Nitra", "Trnava", "Trencin", "Martin", "Poprad", "Prievidza",
	"Zvolen", "Povazska Bystrica", "Nove Zamky", "Michalovce",
}

func main() {
	ifaceName := flag.String("i", "dhcp", "Interface to use")
	count := flag.Int("n", 50, "Number of clients")
	delay := flag.Float64("d", 0.1, "Delay between clients (seconds)")
	flag.Parse()

	log.Printf("--- Starting Go Load Test: %d clients on %s ---", *count, *ifaceName)

	var wg sync.WaitGroup
	successCount := 0
	var mu sync.Mutex

	// Random seed
	rand.Seed(time.Now().UnixNano())

	startTime := time.Now()

	for i := 0; i < *count; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			// Generate random MAC
			mac := net.HardwareAddr{0x02, 0x00, 0x00, byte(rand.Intn(255)), byte(rand.Intn(255)), byte(rand.Intn(255))}
			city := cities[rand.Intn(len(cities))]

			// Use nclient4 for higher level valid client behavior (DORA)
			// Note: nclient4 is more robust but might be slower to initialize per-client than raw socket crafting.
			// Ideally we would reuse socket, but for simulation of distinct clients, separate clients are cleaner logic-wise.

			// Create a client with random MAC
			client, err := nclient4.New(*ifaceName, nclient4.WithHWAddr(mac), nclient4.WithTimeout(5*time.Second))
			if err != nil {
				log.Printf("[%d] Error creating client: %v", id, err)
				return
			}
			defer client.Close()

			// Add Option 82
			modifiers := []dhcpv4.Modifier{
				dhcpv4.WithOption(dhcpv4.OptRelayAgentInfo(
					dhcpv4.OptGeneric(dhcpv4.AgentCircuitIDSubOption, []byte(city)),
				)),
			}

			// Perform DORA
			// Request generates Discover -> Offer -> Request -> Ack
			lease, err := client.Request(context.Background(), modifiers...)
			if err != nil {
				log.Printf("[%d] DORA failed: %v", id, err)
				return
			}

			if (id+1)%10 == 0 {
				log.Printf("[%d/%d] Success (%s) -> Assigned IP: %v", id+1, *count, city, lease.ACK.YourIPAddr)
			}

			mu.Lock()
			successCount++
			mu.Unlock()

		}(i)

		time.Sleep(time.Duration(*delay * float64(time.Second)))
	}

	log.Println("--- Sending Complete. Waiting for remaining transactions... ---")
	wg.Wait()

	duration := time.Since(startTime)
	tps := float64(successCount) / duration.Seconds()

	fmt.Printf("\n--- Load Test Results ---\n")
	fmt.Printf("Clients Simulated: %d\n", *count)
	fmt.Printf("Fully ACKED Leases: %d\n", successCount)
	fmt.Printf("Effective TPS: %.2f leases/sec\n", tps)

	if *count == successCount {
		fmt.Println("SUCCESS: 100% Lease Rate")
	} else {
		fmt.Printf("WARNING: %d failed transactions\n", *count-successCount)
	}
}
