# PLACEHOLDER for dual_logger.py
# Not attached in the chat that scaffolded this repo. Drop your real logger here.
# Role: one Ubuntu machine reads BOTH the Arduino current stream and the ESP32 RTD
# stream, timestamps with ONE clock, writes one merged CSV:
#   unix_s,iso,current_a,current_note,t1_freezer_f,t2_fridge_f,res1_ohm,res2_ohm,fault
# Run: python3 dual_logger.py --current-port /dev/ttyACM0 --temp-port /dev/ttyUSB0 --out ../data/run.csv
