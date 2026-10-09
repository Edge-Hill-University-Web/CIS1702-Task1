# # --- SHIP TELEMETRY INITIALISATION SCRIPT --- 

# TODO: Multiple runtime errors and logic mismatches detected, please fix.
# TRY: pyton -m test -x in the terminal 

# Ship Identity
vessel_name = "Aegis-4"
pilot_callsing = "Starling"
flight_code = pilot_callsign + "-" + vessel_name

# Fuel Calculations
fuel_capacity_litres = "12000.0"
reserve_percentage = 0.15
reserve_fuel = fuel_capacity_litres * reserve_percentage
usable_fuel = fuel_capacity_litres + reserve_fuel

# Payload Weight
crate_count = "25"
crate_weight_kg = 140.5
total_payload_kg = crate_count * crate_weight_kg

# System Manifest
manifest_log = vessel_name + " payload: " + total_payload_kg + " kg"  # Missing string cast

print(r"""
================================================================
   ____  ____  _____ ____      _  _____ ___ ___  _   _
  / __ \|  _ \| ____|  _ \    / \|_   _|_ _/ _ \| \ | |
 | |  | | |_) |  _| | |_) |  / _ \  | |  | | | | |  \| |
 | |__| |  __/| |___|  _ <  / ___ \ | |  | | |_| | |\  |
  \____/|_|   |_____|_| \_\/_/   \_\|_| |___\___/|_| \_|

           D E E P S P A C E   C A R G O

              .        *          .
       *              .       *
                   __________
          ________/__________\_______
     ____/  _    CARGO SHIP    _     \____
    /______/ \________________/ \_________\
       O                             O
              [==]  [==]  [==]

           *** CARGO CONTROL SYSTEM ***
================================================================
""")

print(manifest_log)