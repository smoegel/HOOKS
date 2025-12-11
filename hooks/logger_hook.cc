#include <asiolink/io_address.h>
#include <dhcp/dhcp4.h> // For DHO_ constants
#include <dhcp/option4_addrlst.h>
#include <dhcp/pkt4.h>
#include <dhcpsrv/lease.h> // For Lease4Ptr
#include <fstream>
#include <hooks/hooks.h>
#include <iomanip>
#include <sstream>
#include <string>
#include <sys/stat.h> // For chmod

using namespace isc::hooks;
using namespace isc::dhcp;
using namespace std;

// Define an output file stream for logging
std::ofstream dhcp_log_file;

extern "C" {

// Version function to ensure compatibility
int version() { return (KEA_HOOKS_VERSION); }

// Multi-threading compatibility
int multi_threading_compatible() { return (1); }

// Forward declaration
int pkt4_receive(CalloutHandle &handle);
int pkt4_send(CalloutHandle &handle);
int lease4_select(CalloutHandle &handle);

// Load function: open the log file
int load(LibraryHandle &handle) {
  dhcp_log_file.open("dhcp_hook_log.txt", std::ios::app);
  if (!dhcp_log_file.is_open()) {
    std::cerr << "Failed to open log file" << std::endl;
    return (1); // Fail to load if file can't be opened
  }

  // Set permissions to be world-readable/writable
  chmod("dhcp_hook_log.txt", 0666);

  dhcp_log_file << "Kea Packet Logger Hook Loaded" << std::endl;
  std::cerr << "HOOK DEBUG: Hook Loaded" << std::endl; // Debug to console

  // Explicitly register the callout to ensure it works
  handle.registerCallout("pkt4_receive", pkt4_receive);
  handle.registerCallout("pkt4_send", pkt4_send);
  handle.registerCallout("lease4_select", lease4_select);

  return (0);
}

// Unload function: close the log file
int unload() {
  if (dhcp_log_file.is_open()) {
    dhcp_log_file << "Kea Packet Logger Hook Unloaded" << std::endl;
    dhcp_log_file.close();
  }
  return (0);
}

// Callout for packet reception
int pkt4_receive(CalloutHandle &handle) {
  Pkt4Ptr query4_ptr;
  handle.getArgument("query4", query4_ptr);

  if (dhcp_log_file.is_open()) {
    std::cerr << "HOOK DEBUG: pkt4_receive entered"
              << std::endl; // Debug to console
    dhcp_log_file << "------------------------------------------------"
                  << std::endl;
    dhcp_log_file << "Packet Received at: " << std::time(nullptr) << std::endl;
    dhcp_log_file << "Transaction ID: 0x" << std::hex
                  << query4_ptr->getTransid() << std::dec << std::endl;
    dhcp_log_file << "Packet Type: " << query4_ptr->getType() << std::endl;
    dhcp_log_file << "CIADDR: " << query4_ptr->getCiaddr().toText()
                  << std::endl;
    dhcp_log_file << "YIADDR: " << query4_ptr->getYiaddr().toText()
                  << std::endl;
    dhcp_log_file << "SIADDR: " << query4_ptr->getSiaddr().toText()
                  << std::endl;
    dhcp_log_file << "GIADDR: " << query4_ptr->getGiaddr().toText()
                  << std::endl;
    dhcp_log_file << "CHADDR: " << query4_ptr->getHWAddr()->toText(false)
                  << std::endl;

    // Check for Option 82 (RAIO)
    OptionPtr option82 = query4_ptr->getOption(DHO_DHCP_AGENT_OPTIONS);
    if (option82) {
      dhcp_log_file << "Option 82 Found!" << std::endl;

      // Check if data contains "OLT_TEST"
      // Note: This is a simplified check. Real usage should parse suboptions.
      const std::vector<uint8_t> &data = option82->getData();
      std::string opt82_str(data.begin(), data.end());

      dhcp_log_file << "  Length: " << option82->len() << std::endl;
      dhcp_log_file << "  Data (hex): ";
      for (uint8_t byte : data) {
        dhcp_log_file << std::hex << std::setw(2) << std::setfill('0')
                      << (int)byte;
      }
      dhcp_log_file << std::dec << std::endl;

    } else {
      dhcp_log_file << "No Option 82 present." << std::endl;
    }
  }

  return (0);
}

// Callout for lease selection
int lease4_select(CalloutHandle &handle) {
  Pkt4Ptr query4_ptr;
  Lease4Ptr lease4_ptr;
  handle.getArgument("query4", query4_ptr);
  handle.getArgument("lease4", lease4_ptr);

  if (query4_ptr && lease4_ptr) {
    // Check for Option 82 (RAIO)
    OptionPtr option82 = query4_ptr->getOption(DHO_DHCP_AGENT_OPTIONS);
    if (option82) {
      const std::vector<uint8_t> &data = option82->getData();
      std::string opt82_str(data.begin(), data.end());

      // Check for OLT_TEST string inside the option data
      if (opt82_str.find("OLT_TEST") != std::string::npos) {
        if (dhcp_log_file.is_open()) {
          dhcp_log_file << "  MATCH (lease4_select): OLT_TEST detected. "
                           "Overwriting IP to 192.168.50.100"
                        << std::endl;
        }
        std::cerr << "HOOK DEBUG: OLT_TEST match in lease4_select. Forcing "
                     "192.168.50.100"
                  << std::endl;

        // Force the IP address
        lease4_ptr->addr_ = isc::asiolink::IOAddress("192.168.50.100");
      }
    }
  }
  return (0);
}

// Callout for packet transmission
int pkt4_send(CalloutHandle &handle) {
  Pkt4Ptr response4_ptr;
  handle.getArgument("response4", response4_ptr);

  if (dhcp_log_file.is_open()) {
    std::cerr << "HOOK DEBUG: pkt4_send entered"
              << std::endl; // Debug to console
    dhcp_log_file << "------------------------------------------------"
                  << std::endl;
    dhcp_log_file << "Packet Sent at: " << std::time(nullptr) << std::endl;
    dhcp_log_file << "Transaction ID: 0x" << std::hex
                  << response4_ptr->getTransid() << std::dec << std::endl;
    dhcp_log_file << "Packet Type: " << response4_ptr->getType() << std::endl;
    dhcp_log_file << "CIADDR: " << response4_ptr->getCiaddr().toText()
                  << std::endl;
    dhcp_log_file << "YIADDR (Assigned IP): "
                  << response4_ptr->getYiaddr().toText() << std::endl;
    dhcp_log_file << "SIADDR: " << response4_ptr->getSiaddr().toText()
                  << std::endl;
    dhcp_log_file << "GIADDR: " << response4_ptr->getGiaddr().toText()
                  << std::endl;
    dhcp_log_file << "CHADDR: " << response4_ptr->getHWAddr()->toText(false)
                  << std::endl;

    // Check for Option 82 in response (if echoed)
    OptionPtr option82 = response4_ptr->getOption(DHO_DHCP_AGENT_OPTIONS);
    if (option82) {
      dhcp_log_file << "Option 82 included in response." << std::endl;
    }
  }

  return (0);
}

} // extern "C"
