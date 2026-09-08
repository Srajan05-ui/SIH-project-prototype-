"""
live_proof.py — Run this in front of judges to prove the data is real!

This script connects directly to Google Flights and prints live, 
real-time prices for the airlines. Anyone can open Google Flights on 
their phone at the exact same moment and verify the prices match.
"""
import time
from fast_flights import FlightQuery, Passengers, get_flights, create_query
from datetime import date, timedelta

print("\n" + "="*70)
print(" LIVE PROOF: Fetching Real-Time Fares")
print(" Source: Google Flights (Aggregating IndiGo, Air India, Akasa, SpiceJet)")
print("="*70)

routes = [("DEL", "BOM"), ("BOM", "BLR"), ("DEL", "BLR")]

for origin, dest in routes:
    # Check fares for exactly 7 days from today
    dep = (date.today() + timedelta(days=7)).isoformat()
    
    q = create_query(
        flights=[FlightQuery(date=dep, from_airport=origin, to_airport=dest)],
        trip="one-way",
        seat="economy",
        passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
        currency="INR",
    )
    
    result = get_flights(q)
    flights = result if isinstance(result, list) else (getattr(result, "flights", None) or [])

    seen = {}
    for f in flights:
        price_raw = getattr(f, "price", None)
        airlines = getattr(f, "airlines", [])
        airline = airlines[0] if airlines else getattr(f, "airline", "?")
        if price_raw and airline not in seen:
            try:
                # Clean the price string (e.g. "₹6,425" -> 6425.0)
                val = float("".join(c for c in str(price_raw) if c.isdigit() or c == "."))
                if val >= 500:  # Ignore weird USD glitches
                    seen[str(airline)] = val
            except ValueError:
                pass

    print(f"\n  Route: {origin} -> {dest}  |  Departure: {dep}")
    print(f"  {'-'*50}")
    
    if not seen:
        print("    No flights found for this route.")
    else:
        for airline, price in sorted(seen.items(), key=lambda x: x[1]):
            print(f"    {airline:<25} ₹{price:>8,.0f}")
        print(f"  Total unique airlines: {len(seen)}")
    
    time.sleep(3) # Small delay to be polite to the server

print("\n✅ Live proof complete. Ask the judges to check these prices on their phones!")
