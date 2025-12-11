# Správa Verzií a Vývojový Workflow (Git Guide)

Tento dokument slúži ako návod na správne návyky pri rozširovaní projektu pomocou systému Git. Cieľom je udržiavať hlavnú vetvu (`master`) vždy funkčnú a stabilnú, zatiaľ čo vývoj prebieha v oddelených vetvách.

## 1. Začiatok novej úlohy (Feature Branch)

Nikdy nerobte zmeny priamo v `master` vetve, ak ide o väčšiu úpravu alebo novú funkcionalitu. Namiesto toho si vytvorte novú "feature" vetvu.

1. **Uistite sa, že ste na aktuálnom masteri:**
   ```bash
   git checkout master
   git pull github master  # Stiahnutie prípadných zmien zo servera
   ```

2. **Vytvorte novú vetvu:**
   Pomenujte ju podľa toho, čo idete robiť (napr. `feature/pridanie-option-60`, `fix/oprava-logovania`).
   ```bash
   git checkout -b feature/nazov-vasej-upray
   ```

## 2. Vývoj a Zmeny (Development Loop)

Teraz pracujete vo svojej vetve. Môžete meniť súbory, kompilovať a testovať bez toho, aby ste rozbili hlavný projekt.

1. **Vykonajte zmeny v kóde.**
2. **Otestujte zmeny:**
   - Prekompilovať (`make`)
   - Nasadiť (`sudo cp ...`)
   - Spustiť testy (`python3 sim_client.py ...`)
3. **Uložte zmeny (Commit):**
   ```bash
   git add .
   git commit -m "Popis toho, čo sa zmenilo (napr. Pridaná podpora pre Option 60)"
   ```
   *Tip: Robte radšej menšie a častejšie commity ako jeden obrovský na konci.*

## 3. Ukončenie práce a Zlúčenie (Merge)

Keď je funkcia hotová a otestovaná, je čas ju začleniť späť do hlavnej vetvy `master`.

### Možnosť A: Lokálny Merge (Pre jedného vývojára)
Ak pracujete sami, najrýchlejšie je zlúčiť veny lokálne.

1. **Prepnite sa späť na master:**
   ```bash
   git checkout master
   ```

2. **Zlúčte vašu vetvu:**
   ```bash
   git merge feature/nazov-vasej-upray
   ```
   *Ak Git nahlási konflikty, musíte ich vyriešiť otvorením označených súborov, úpravou a následným `git commit`.*

3. **Upracovanie (Voliteľné):**
   Ak už vetvu nepotrebujete:
   ```bash
   git branch -d feature/nazov-vasej-upray
   ```

### Možnosť B: Pull Request (Best Practice pre tímy / GitHub)
Ak chcete využiť GitHub naplno (Code Review, história), použite Pull Request.

1. **Pushnite vašu vetvu na GitHub:**
   ```bash
   git push -u github feature/nazov-vasej-upray
   ```
2. **Vytvorte Pull Request cez CLI:**
   ```bash
   gh pr create --title "Názov zmeny" --body "Popis zmeny"
   ```
3. **Schválenie a Merge:**
   Na webe GitHubu alebo cez `gh pr merge` zlúčite zmeny do mastera.

## 4. Synchronizácia so serverom

Po lokálnom merge (Možnosť A) nezabudnite poslať aktualizovaný `master` na GitHub:

```bash
git checkout master
git push github master
```

## Zhrnutie Workflow

1. `git checkout -b feature/nova-vec`
2. ... kódovanie, testovanie (`make`, `cp` ...) ...
3. `git add .` + `git commit`
4. `git checkout master`
5. `git merge feature/nova-vec`
6. `git push github master`
