# Návod na inštaláciu a spustenie Kea DHCP Hook projektu

Tento dokument obsahuje kroky na inštaláciu Kea DHCP servera, kompiláciu vytvoreného hooku a spustenie simulácie.

## 1. Požiadavky a Inštalácia

Cieľový OS: Linux Mint Debian Edition (LMDE) / Debian

### Inštalácia Kea DHCP Server a závislostí
Budeme potrebovať Kea server, vývojové hlavičky (pre kompiláciu hooku) a Python Scapy pre simuláciu.

```bash
# Aktualizácia repozitárov
sudo apt-get update

# Inštalácia Kea, C++ kompilátora a potrebných knižníc
sudo apt-get install -y kea-dhcp4-server kea-dev build-essential python3-scapy python3-pip libboost-dev libboost-system-dev

# Vytvorenie dedikovaného interface "dhcp"
sudo ip link add dhcp type dummy
sudo ip link set dhcp up
sudo ip addr add 192.168.50.1/24 dev dhcp
```

*Poznámka: Ak balíčky `kea-dhcp4-server` alebo `kea-dev` nie sú v repozitároch, je potrebné ich stiahnuť z ISC repozitára (cloudsmith.io), ale na Debian/LMDE by mali byť dostupné v štandardných alebo backports repozitároch.*

## 2. Kompilácia Hooku

Prejdite do adresára s hook zdrojovým kódom a skompilujte ho:

```bash
cd /home/manyo/Devel/hooks/hooks
make
```

Ak všetko prebehne v poriadku, vznikne súbor `libdhcp_logger.so`.

Z dôvodu bezpečnostných nastavení Kea (na tomto systéme) je nutné umiestniť knižnicu do systémového adresára pre hooky:

```bash
sudo cp libdhcp_logger.so /usr/lib/x86_64-linux-gnu/kea/hooks/
```

*Poznámka: Ak upravíte zdrojový kód (napr. logger_hook.cc), musíte znova spustiť `make` a znova skopírovať knižnicu na toto miesto.*

## 3. Konfigurácia Kea

Vytvorte konfiguračný súbor pre Kea, napríklad `kea-with-hook.conf`.
**Dôležité**: Upravte cesty a interface podľa vášho systému.

```json
{
"Dhcp4": {
    "interfaces-config": {
        "interfaces": ["*"]
    },
    "lease-database": {
        "type": "memfile",
        "lfc-interval": 3600
    },
    "valid-lifetime": 4000,
    "subnet4": [
        {
            "id": 1,
            "subnet": "192.168.50.0/24",
            "pools": [ { "pool": "192.168.50.10 - 192.168.50.100" } ]
        }
    ],
    "hooks-libraries": [
        {
            "library": "/usr/lib/x86_64-linux-gnu/kea/hooks/libdhcp_logger.so"
        }
    ],
    "loggers": [
    {
        "name": "kea-dhcp4",
        "output_options": [
            {
                "output": "stdout"
            }
        ],
        "severity": "INFO",
        "debuglevel": 0
    }
  ]
}
}
```

## 4. Spustenie Servera

Spustite Kea server s touto konfiguráciou. Odporúčam spustiť v popredí pre sledovanie výstupu:

```bash
sudo KEA_LOCKFILE_DIR=/tmp KEA_PIDFILE_DIR=/tmp kea-dhcp4 -c kea-with-hook.conf
```

Mali by ste vidieť hlášku: `Kea Packet Logger Hook Loaded`.

## 5. Spustenie Simulácie

V druhom termináli spustite Python skript na odoslanie DHCP Discover paketu.
**Pozor**: Musíte špecifikovať existujúci sieťový interface cez parameter `-i`.
Zistite názov vášho interface príkazom `ip a` (napr. `enp0s31f6`, `wlp61s0`, `lo`...).

```bash
cd /home/manyo/Devel/hooks/client

# Príklad: použitie dedikovaného interface 'dhcp'
sudo python3 sim_client.py -i dhcp

# S Option 82 (Circuit ID "test_link")
sudo python3 sim_client.py -i enp0s31f6 -o test_link
```

## 6. Overenie

Skontrolujte vytvorený log súbor v adresári, odkiaľ ste spustili Kea server (pravdepodobne `/home/manyo/Devel/hooks` alebo domovský priečinok, ak ste nespustili `cd`):

```bash
cat dhcp_hook_log.txt
```

Mali by ste vidieť záznamy o prijatých paketoch a dekódované Option 82 dáta.
