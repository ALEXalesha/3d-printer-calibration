// Made by tools/build_data.py from profiles/*.json and VERSION - do not edit by hand.
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  C3D.data = {
 "version": "1.0.0",
 "printers": [
  {
   "id": "elegoo-centauri-carbon",
   "name": "Elegoo Centauri Carbon",
   "prefix": "ECC",
   "verified": true,
   "source": "Start/end code of a real ElegooSlicer 1.5.3.5 print, profile 'Elegoo Centauri Carbon 0.4 nozzle'. All 10 tests printed on this printer on 2026-10-02.",
   "bed": {
    "x": 256.0,
    "y": 256.0,
    "z": 256.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "klipper",
   "max_speed": 500.0,
   "max_accel": 20000,
   "default_accel": 5000,
   "travel_speed": 300.0,
   "z_speed": 150.0,
   "retract": {
    "length": 0.8,
    "speed": 30.0,
    "z_hop": 0.4
   },
   "options": {
    "canvas": true,
    "nozzle_wipe": true
   },
   "start_state": {
    "x": 177.0,
    "y": -1.2,
    "z": 0.6,
    "e": 42.408,
    "time": 240.0
   },
   "start_gcode": [
    "M106 S0 ; disable fan",
    "M106 P2 S0 ; disable additional fan",
    ";===== CC_START_GCODE (как ElegooSlicer, профиль Centauri Carbon 0.4) =====",
    ";printer_model:Elegoo Centauri Carbon",
    ";initial_filament:{filament_type}",
    ";bed_level_temp:{bed_temp}",
    "M400 ; wait for buffer to clear",
    "M220 S100 ;Set the feed speed to 100%",
    "M221 S100 ;Set the flow rate to 100%",
    "M104 S140",
    "M140 S{bed_temp}",
    "G90",
    "M83",
    "G28 ;home",
    "{?nozzle_wipe}M729 ;Clean Nozzle",
    "M190 S{bed_temp}",
    "",
    "M109 S{first_layer_nozzle_temp}",
    "{?canvas}M6211 A1 L200 T0 Q{first_layer_nozzle_temp} R{first_layer_nozzle_temp} S{first_layer_nozzle_temp}",
    "T0",
    "{?pla_hot_bed}M106 P3 S255 ;Prevent PLA from jamming",
    "M204 S{accel} ;acceleration",
    "G1 X128 Y-1.2 F20000",
    "G1 Z0.3 F900",
    "G90",
    "M83",
    "G92 E0 ;Reset Extruder",
    "G1 F{purge_f1}",
    "G1 X0 E10.156 ;Draw the first line",
    "G1 Y98.8 E7.934",
    "G1 X0.9 Y100 E0.1",
    "G1 Y-0.3 E7.934",
    "G1 X78 E6.284",
    "G1 F{purge_f2_slow}",
    "G1 X98 E2",
    "G1 F{purge_f2}",
    "G1 X118 E2",
    "G1 F{purge_f2_slow}",
    "G1 X138 E2",
    "G1 F{purge_f2}",
    "G1 X158 E2",
    "G1 F{purge_f2}",
    "G1 X178 E2",
    "G3 I-1 J0 Z0.6 F1200.0 ;Move to side a little",
    "G1 F20000",
    "G92 E0 ;Reset Extruder",
    "SET_PRINT_STATS_INFO TOTAL_LAYER={total_layers} CURRENT_LAYER=0",
    ";LAYER_COUNT:{total_layers}"
   ],
   "end_gcode": [
    "M106 S0 ; disable fan",
    ";===== CC_END_GCODE =====",
    "M400 ; wait for buffer to clear",
    "M140 S0 ;Turn-off bed",
    "M106 S255 ;Cooling nozzle",
    "M83",
    "G92 E0 ; zero the extruder",
    "G1 E-0.8 F1800",
    "G2 I1 J0 Z{max_z_plus_half} F3000 ; lower z a little",
    "G90",
    "G1 Z{max_z_plus_50_capped} F20000 ; Move print head up",
    "M204 S5000",
    "M749",
    "M204 S5000",
    "M400",
    "M83",
    "G1 X202 F20000",
    "M400",
    "G1 Y250 F20000",
    "G1 Y264.5 F1200",
    "M400",
    "G92 E0",
    "M104 S0 ;Turn-off hotend",
    "M140 S0 ;Turn-off bed",
    "M106 S0 ; turn off fan",
    "M106 P2 S0 ; turn off remote part cooling fan",
    "M106 P3 S0 ; turn off chamber cooling fan",
    "M84 ;Disable all steppers"
   ]
  },
  {
   "id": "bambu-a1",
   "name": "Bambu Lab A1",
   "prefix": "BA1",
   "verified": false,
   "source": "Build volume: bambulab.com A1 specifications. Start code written for this project.",
   "bed": {
    "x": 256.0,
    "y": 256.0,
    "z": 256.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "marlin",
   "max_speed": 500.0,
   "max_accel": 10000,
   "default_accel": 5000,
   "travel_speed": 300.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.8,
    "speed": 30.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ],
   "warning": "Bambu Lab firmware has its own G-code dialect and file headers. Only plain .gcode over SD card or LAN; prefer importing your own Bambu Studio G-code. Not checked on a real printer. Check this preset by importing a G-code your printer has already printed well (step 1, 'Load your G-code')."
  },
  {
   "id": "bambu-p1s",
   "name": "Bambu Lab P1S",
   "prefix": "BP1S",
   "verified": false,
   "source": "Build volume: bambulab.com P1S specifications. Start code written for this project.",
   "bed": {
    "x": 256.0,
    "y": 256.0,
    "z": 256.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "marlin",
   "max_speed": 500.0,
   "max_accel": 20000,
   "default_accel": 5000,
   "travel_speed": 300.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.8,
    "speed": 30.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ],
   "warning": "Bambu Lab firmware has its own G-code dialect and file headers. Only plain .gcode over SD card or LAN; prefer importing your own Bambu Studio G-code. Not checked on a real printer. Check this preset by importing a G-code your printer has already printed well (step 1, 'Load your G-code')."
  },
  {
   "id": "bambu-x1c",
   "name": "Bambu Lab X1 Carbon",
   "prefix": "BX1C",
   "verified": false,
   "source": "Build volume: bambulab.com X1 Carbon specifications. Start code written for this project.",
   "bed": {
    "x": 256.0,
    "y": 256.0,
    "z": 256.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "marlin",
   "max_speed": 500.0,
   "max_accel": 20000,
   "default_accel": 5000,
   "travel_speed": 300.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.8,
    "speed": 30.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ],
   "warning": "Bambu Lab firmware has its own G-code dialect and file headers. Only plain .gcode over SD card or LAN; prefer importing your own Bambu Studio G-code. Not checked on a real printer. Check this preset by importing a G-code your printer has already printed well (step 1, 'Load your G-code')."
  },
  {
   "id": "creality-ender3-v3",
   "name": "Creality Ender-3 V3",
   "prefix": "E3V3",
   "verified": false,
   "source": "Build volume: creality.com Ender-3 V3 specifications (Klipper-based firmware). Start code written for this project.",
   "bed": {
    "x": 220.0,
    "y": 220.0,
    "z": 250.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "klipper",
   "max_speed": 600.0,
   "max_accel": 20000,
   "default_accel": 5000,
   "travel_speed": 300.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.8,
    "speed": 40.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "SET_PRINT_STATS_INFO TOTAL_LAYER={total_layers}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ],
   "warning": "Not checked on a real printer. Check this preset by importing a G-code your printer has already printed well (step 1, 'Load your G-code')."
  },
  {
   "id": "creality-k1",
   "name": "Creality K1",
   "prefix": "K1",
   "verified": false,
   "source": "Build volume: creality.com K1 specifications (Klipper-based firmware). Start code written for this project.",
   "bed": {
    "x": 220.0,
    "y": 220.0,
    "z": 250.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "klipper",
   "max_speed": 600.0,
   "max_accel": 20000,
   "default_accel": 5000,
   "travel_speed": 300.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.8,
    "speed": 40.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "SET_PRINT_STATS_INFO TOTAL_LAYER={total_layers}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ],
   "warning": "Not checked on a real printer. Check this preset by importing a G-code your printer has already printed well (step 1, 'Load your G-code')."
  },
  {
   "id": "generic-delta-klipper",
   "name": "Generic Delta (Klipper)",
   "prefix": "GDK",
   "verified": false,
   "source": "Generic profile of this project: minimal safe start code, no vendor commands. Round bed, origin in the centre.",
   "bed": {
    "x": 200.0,
    "y": 200.0,
    "z": 300.0,
    "origin": "center",
    "shape": "round"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "klipper",
   "max_speed": 300.0,
   "max_accel": 5000,
   "default_accel": 2000,
   "travel_speed": 200.0,
   "z_speed": 50.0,
   "retract": {
    "length": 0.8,
    "speed": 35.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "SET_PRINT_STATS_INFO TOTAL_LAYER={total_layers}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ]
  },
  {
   "id": "generic-klipper",
   "name": "Generic Klipper",
   "prefix": "GKL",
   "verified": false,
   "source": "Generic profile of this project: minimal safe start code, no vendor commands.",
   "bed": {
    "x": 220.0,
    "y": 220.0,
    "z": 250.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "klipper",
   "max_speed": 300.0,
   "max_accel": 10000,
   "default_accel": 3000,
   "travel_speed": 250.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.8,
    "speed": 35.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "SET_PRINT_STATS_INFO TOTAL_LAYER={total_layers}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ]
  },
  {
   "id": "generic-marlin",
   "name": "Generic Marlin",
   "prefix": "GMA",
   "verified": false,
   "source": "Generic profile of this project: minimal safe start code, no vendor commands. Retraction 5 mm suits a Bowden extruder; set about 1 mm for direct drive.",
   "bed": {
    "x": 220.0,
    "y": 220.0,
    "z": 250.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "marlin",
   "max_speed": 200.0,
   "max_accel": 3000,
   "default_accel": 1000,
   "travel_speed": 150.0,
   "z_speed": 10.0,
   "retract": {
    "length": 5.0,
    "speed": 40.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ]
  },
  {
   "id": "generic-rrf",
   "name": "Generic RepRapFirmware",
   "prefix": "GRR",
   "verified": false,
   "source": "Generic profile of this project: minimal safe start code, no vendor commands.",
   "bed": {
    "x": 230.0,
    "y": 230.0,
    "z": 250.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "rrf",
   "max_speed": 300.0,
   "max_accel": 5000,
   "default_accel": 2000,
   "travel_speed": 200.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.8,
    "speed": 35.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ]
  },
  {
   "id": "prusa-mk3s",
   "name": "Prusa MK3S+",
   "prefix": "MK3S",
   "verified": false,
   "source": "Build volume: prusa3d.com Original Prusa i3 MK3S+ specifications; G80 and M900 (Linear Advance 1.5): Prusa firmware G-code reference. Start code written for this project.",
   "bed": {
    "x": 250.0,
    "y": 210.0,
    "z": 210.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "marlin",
   "max_speed": 200.0,
   "max_accel": 2500,
   "default_accel": 1250,
   "travel_speed": 180.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.8,
    "speed": 35.0,
    "z_hop": 0.2
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "G80 ; mesh bed leveling",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ],
   "warning": "Not checked on a real printer. Check this preset by importing a G-code your printer has already printed well (step 1, 'Load your G-code')."
  },
  {
   "id": "prusa-mk4",
   "name": "Prusa MK4",
   "prefix": "MK4",
   "verified": false,
   "source": "Build volume: prusa3d.com Original Prusa MK4 specifications; M572 S (pressure advance) and G29: Prusa firmware G-code reference (help.prusa3d.com). Start code written for this project.",
   "bed": {
    "x": 250.0,
    "y": 210.0,
    "z": 220.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "marlin",
   "max_speed": 300.0,
   "max_accel": 5000,
   "default_accel": 2500,
   "travel_speed": 200.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.7,
    "speed": 35.0,
    "z_hop": 0.2
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "G29 ; mesh bed leveling",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ],
   "warning": "Not checked on a real printer. Check this preset by importing a G-code your printer has already printed well (step 1, 'Load your G-code').",
   "fw_overrides": {
    "pressure_advance": "M572 S{v}"
   }
  },
  {
   "id": "sovol-sv06",
   "name": "Sovol SV06",
   "prefix": "SV06",
   "verified": false,
   "source": "Build volume: sovol3d.com SV06 specifications; G29: Marlin documentation (marlinfw.org/docs/gcode/G029.html). Start code written for this project.",
   "bed": {
    "x": 220.0,
    "y": 220.0,
    "z": 250.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "marlin",
   "max_speed": 180.0,
   "max_accel": 2000,
   "default_accel": 1000,
   "travel_speed": 150.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.8,
    "speed": 40.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "G29 ; auto bed leveling",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ],
   "warning": "Not checked on a real printer. Check this preset by importing a G-code your printer has already printed well (step 1, 'Load your G-code')."
  },
  {
   "id": "voron-24-300",
   "name": "Voron 2.4 (300 mm)",
   "prefix": "V24",
   "verified": false,
   "source": "Build volume: Voron Design 2.4 documentation (docs.vorondesign.com). QUAD_GANTRY_LEVEL: Klipper G-code reference. Start code written for this project.",
   "bed": {
    "x": 300.0,
    "y": 300.0,
    "z": 280.0,
    "origin": "corner",
    "shape": "rect"
   },
   "nozzle": 0.4,
   "filament_diameter": 1.75,
   "firmware": "klipper",
   "max_speed": 500.0,
   "max_accel": 10000,
   "default_accel": 4000,
   "travel_speed": 300.0,
   "z_speed": 10.0,
   "retract": {
    "length": 0.5,
    "speed": 35.0,
    "z_hop": 0.4
   },
   "options": {},
   "start_gcode": [
    "; Start code made by Calibrate 3D Printer: home, heat, purge line. Compare it with your slicer's.",
    "G90",
    "M83",
    "M140 S{bed_temp}",
    "M104 S150",
    "G28",
    "QUAD_GANTRY_LEVEL",
    "G28 Z",
    "M190 S{bed_temp}",
    "M109 S{first_layer_nozzle_temp}",
    "{set_accel}",
    "SET_PRINT_STATS_INFO TOTAL_LAYER={total_layers}",
    "G92 E0",
    "G1 Z5 F{z_f}",
    "G1 X{purge_x0} Y{purge_y0} F{travel_f}",
    "G1 Z0.3 F{z_f}",
    "G1 X{purge_x1} Y{purge_y1} E{purge_e} F1500",
    "G1 X{purge_x2} Y{purge_y2} F{travel_f}",
    "G1 X{purge_x3} Y{purge_y3} E{purge_e} F1500",
    "G92 E0",
    "G1 Z2 F{z_f}"
   ],
   "end_gcode": [
    "; End code made by Calibrate 3D Printer",
    "M104 S0",
    "M140 S0",
    "M106 S0",
    "G91",
    "G1 E-2 F1800",
    "G90",
    "G1 Z{park_z} F{z_f}",
    "G1 X{park_x} Y{park_y} F{travel_f}",
    "M84"
   ],
   "warning": "Not checked on a real printer. Check this preset by importing a G-code your printer has already printed well (step 1, 'Load your G-code')."
  }
 ],
 "materials": [
  {
   "id": "pla",
   "type": "PLA",
   "name": "PLA",
   "verified": true,
   "note": "the author's tested preset (Generic PLA @Elegoo Centauri)",
   "tower": {
    "start": 230,
    "end": 190,
    "step": 5
   },
   "nozzle_temp": 210,
   "first_layer_temp": 210,
   "bed": 60,
   "flow": 0.98,
   "mvs": 21.0,
   "fan": 1.0,
   "bridge_fan": 1.0,
   "fan_off_layers": 1,
   "min_layer_time": 4.0,
   "pa_default": 0.024,
   "density": 1.24,
   "max_flow": [
    8.0,
    40.0
   ]
  },
  {
   "id": "petg",
   "type": "PETG",
   "name": "PETG",
   "verified": true,
   "note": "the author's tested preset (Generic PETG @Elegoo Centauri)",
   "tower": {
    "start": 260,
    "end": 220,
    "step": 5
   },
   "nozzle_temp": 255,
   "first_layer_temp": 255,
   "bed": 80,
   "flow": 1.0,
   "mvs": 10.0,
   "fan": 0.5,
   "bridge_fan": 1.0,
   "fan_off_layers": 3,
   "min_layer_time": 8.0,
   "pa_default": 0.02,
   "density": 1.27,
   "max_flow": [
    4.0,
    28.0
   ]
  },
  {
   "id": "abs",
   "type": "ABS",
   "name": "ABS",
   "verified": false,
   "note": "generic values",
   "tower": {
    "start": 260,
    "end": 220,
    "step": 5
   },
   "nozzle_temp": 250,
   "first_layer_temp": 250,
   "bed": 100,
   "flow": 0.95,
   "mvs": 16.0,
   "fan": 0.2,
   "bridge_fan": 0.5,
   "fan_off_layers": 3,
   "min_layer_time": 10.0,
   "pa_default": 0.02,
   "density": 1.04,
   "max_flow": [
    4.0,
    28.0
   ]
  },
  {
   "id": "asa",
   "type": "ASA",
   "name": "ASA",
   "verified": false,
   "note": "generic values",
   "tower": {
    "start": 270,
    "end": 230,
    "step": 5
   },
   "nozzle_temp": 260,
   "first_layer_temp": 260,
   "bed": 100,
   "flow": 0.95,
   "mvs": 16.0,
   "fan": 0.3,
   "bridge_fan": 0.6,
   "fan_off_layers": 3,
   "min_layer_time": 10.0,
   "pa_default": 0.02,
   "density": 1.07,
   "max_flow": [
    4.0,
    28.0
   ]
  },
  {
   "id": "tpu",
   "type": "TPU",
   "name": "TPU 95A",
   "verified": false,
   "note": "generic values; print slowly, direct drive only",
   "tower": {
    "start": 240,
    "end": 200,
    "step": 5
   },
   "nozzle_temp": 225,
   "first_layer_temp": 225,
   "bed": 40,
   "flow": 1.0,
   "mvs": 3.5,
   "fan": 0.6,
   "bridge_fan": 1.0,
   "fan_off_layers": 1,
   "min_layer_time": 10.0,
   "pa_default": 0.05,
   "density": 1.21,
   "max_flow": [
    1.0,
    9.0
   ]
  }
 ],
 "firmware": {
  "_comment": "Every firmware-dependent command lives here and nowhere else in the code. Placeholders: {v} pressure advance (3 decimals), {a} acceleration mm/s2 (integer), {s255} fan 0-255, {s1} fan 0.00-1.00, {total} layers, {n} current layer (1-based). 'signature' lists command words that belong to this firmware only: the G-code check flags them in a profile of another firmware. 'checked' is the date the link was read; null means 'проверить' (not checked against the documentation yet).",
  "klipper": {
   "name": "Klipper",
   "pressure_advance": "SET_PRESSURE_ADVANCE ADVANCE={v}",
   "accel": [
    "SET_VELOCITY_LIMIT ACCEL={a}"
   ],
   "accel_band": [
    "SET_VELOCITY_LIMIT ACCEL={a}",
    "M204 S{a}"
   ],
   "layer_progress": "SET_PRINT_STATS_INFO TOTAL_LAYER={total} CURRENT_LAYER={n}",
   "fan": "M106 S{s255}",
   "signature": [
    "SET_PRESSURE_ADVANCE",
    "SET_VELOCITY_LIMIT",
    "SET_PRINT_STATS_INFO"
   ],
   "docs": {
    "pressure_advance": {
     "url": "https://www.klipper3d.org/G-Codes.html#set_pressure_advance",
     "checked": "2026-10-03"
    },
    "accel": {
     "url": "https://www.klipper3d.org/G-Codes.html#set_velocity_limit",
     "checked": "2026-10-03"
    },
    "accel_band": {
     "url": "https://www.klipper3d.org/G-Codes.html#g-code-commands",
     "checked": "2026-10-03"
    },
    "layer_progress": {
     "url": "https://www.klipper3d.org/G-Codes.html#set_print_stats_info",
     "checked": "2026-10-03"
    },
    "fan": {
     "url": "https://www.klipper3d.org/G-Codes.html#g-code-commands",
     "checked": "2026-10-03"
    }
   }
  },
  "marlin": {
   "name": "Marlin",
   "pressure_advance": "M900 K{v}",
   "accel": [
    "M204 S{a}"
   ],
   "accel_band": [
    "M204 S{a}"
   ],
   "layer_progress": null,
   "fan": "M106 S{s255}",
   "signature": [
    "M900"
   ],
   "docs": {
    "pressure_advance": {
     "url": "https://marlinfw.org/docs/gcode/M900.html",
     "checked": "2026-10-03"
    },
    "accel": {
     "url": "https://marlinfw.org/docs/gcode/M204.html",
     "checked": "2026-10-03",
     "note": "S is the legacy form (print and travel together); still accepted"
    },
    "accel_band": {
     "url": "https://marlinfw.org/docs/gcode/M204.html",
     "checked": "2026-10-03"
    },
    "fan": {
     "url": "https://marlinfw.org/docs/gcode/M106.html",
     "checked": "2026-10-03"
    }
   }
  },
  "rrf": {
   "name": "RepRapFirmware",
   "pressure_advance": "M572 D0 S{v}",
   "accel": [
    "M204 P{a} T{a}"
   ],
   "accel_band": [
    "M204 P{a} T{a}"
   ],
   "layer_progress": null,
   "fan": "M106 S{s1}",
   "signature": [
    "M572"
   ],
   "docs": {
    "pressure_advance": {
     "url": "https://docs.duet3d.com/User_manual/Reference/Gcodes#m572-set-or-report-extruder-pressure-advance",
     "checked": null
    },
    "accel": {
     "url": "https://docs.duet3d.com/User_manual/Reference/Gcodes#m204-set-printing-and-travel-accelerations",
     "checked": null
    },
    "accel_band": {
     "url": "https://docs.duet3d.com/User_manual/Reference/Gcodes#m204-set-printing-and-travel-accelerations",
     "checked": null
    },
    "fan": {
     "url": "https://docs.duet3d.com/User_manual/Reference/Gcodes#m106-fan-on",
     "checked": null
    },
    "_note": "docs.duet3d.com did not render for the agent on 2026-10-03: проверить"
   }
  }
 },
 "schema": {
  "_comment": "Fields of printer and material profiles. type: str, num, int, bool, enum, lines (list of strings), list (list of numbers). Both editions check profiles against this file (calib3d/core/profiles.py, web/js/core/profiles.js).",
  "printer": [
   [
    "id",
    "str"
   ],
   [
    "name",
    "str"
   ],
   [
    "prefix",
    "str"
   ],
   [
    "verified",
    "bool"
   ],
   [
    "bed.x",
    "num",
    50,
    1000
   ],
   [
    "bed.y",
    "num",
    50,
    1000
   ],
   [
    "bed.z",
    "num",
    50,
    1000
   ],
   [
    "bed.origin",
    "enum",
    [
     "corner",
     "center"
    ]
   ],
   [
    "bed.shape",
    "enum",
    [
     "rect",
     "round"
    ]
   ],
   [
    "nozzle",
    "num",
    0.1,
    1.2
   ],
   [
    "filament_diameter",
    "num",
    1.5,
    3.0
   ],
   [
    "firmware",
    "enum",
    [
     "klipper",
     "marlin",
     "rrf"
    ]
   ],
   [
    "max_speed",
    "num",
    20,
    2000
   ],
   [
    "max_accel",
    "int",
    100,
    100000
   ],
   [
    "default_accel",
    "int",
    100,
    100000
   ],
   [
    "travel_speed",
    "num",
    20,
    2000
   ],
   [
    "z_speed",
    "num",
    1,
    500
   ],
   [
    "retract.length",
    "num",
    0,
    15
   ],
   [
    "retract.speed",
    "num",
    5,
    150
   ],
   [
    "retract.z_hop",
    "num",
    0,
    5
   ],
   [
    "start_gcode",
    "lines"
   ],
   [
    "end_gcode",
    "lines"
   ]
  ],
  "printer_optional": [
   [
    "source",
    "str"
   ],
   [
    "options",
    "flags"
   ],
   [
    "start_state",
    "state"
   ],
   [
    "fw_overrides",
    "overrides"
   ],
   [
    "warning",
    "str"
   ]
  ],
  "material": [
   [
    "id",
    "str"
   ],
   [
    "type",
    "str"
   ],
   [
    "name",
    "str"
   ],
   [
    "verified",
    "bool"
   ],
   [
    "tower.start",
    "int",
    150,
    350
   ],
   [
    "tower.end",
    "int",
    150,
    350
   ],
   [
    "tower.step",
    "int",
    1,
    20
   ],
   [
    "nozzle_temp",
    "int",
    150,
    350
   ],
   [
    "first_layer_temp",
    "int",
    150,
    350
   ],
   [
    "bed",
    "int",
    0,
    130
   ],
   [
    "flow",
    "num",
    0.5,
    1.5
   ],
   [
    "mvs",
    "num",
    0.5,
    60
   ],
   [
    "fan",
    "num",
    0,
    1
   ],
   [
    "bridge_fan",
    "num",
    0,
    1
   ],
   [
    "fan_off_layers",
    "int",
    0,
    10
   ],
   [
    "min_layer_time",
    "num",
    0,
    60
   ],
   [
    "pa_default",
    "num",
    0,
    2
   ],
   [
    "density",
    "num",
    0.8,
    2.0
   ],
   [
    "max_flow",
    "list",
    0.5,
    80
   ]
  ]
 },
 "tables": {
  "_comment": "tan_deg[a] = math.tan(math.radians(a)) as exact hex (float.fromhex / num.js parseHexDouble). Made once by CPython on Windows, so both editions use the same bits.",
  "tan_deg": [
   "0x0.0p+0",
   "0x1.1dfbd9410a422p-6",
   "0x1.1e12295d61fc2p-5",
   "0x1.ad53144273e73p-5",
   "0x1.1e6b93a693204p-4",
   "0x1.665a8349d55e1p-4",
   "0x1.ae81c75231d98p-4",
   "0x1.f6ecf19881d32p-4",
   "0x1.1fd3df8664fe5p-3",
   "0x1.445f0fbb1cf91p-3",
   "0x1.691e1ebc5cbbcp-3",
   "0x1.8e174375dceb6p-3",
   "0x1.b350dac76234cp-3",
   "0x1.d8d16c1491594p-3",
   "0x1.fe9fae1181f54p-3",
   "0x1.126145e9ecd56p-2",
   "0x1.25a0951873b22p-2",
   "0x1.391176b8feb5bp-2",
   "0x1.4cb7bfb4961aep-2",
   "0x1.60976af8c1613p-2",
   "0x1.74b49cf3902d4p-2",
   "0x1.8913a75259d06p-2",
   "0x1.9db90d0ac0d40p-2",
   "0x1.b2a986b66229fp-2",
   "0x1.c7ea074a90a0ep-2",
   "0x1.dd7fc13699ab1p-2",
   "0x1.f3702bf455cf4p-2",
   "0x1.04e0850c1dd5cp-1",
   "0x1.103c37f7ebedcp-1",
   "0x1.1bce655fbb9bfp-1",
   "0x1.279a74590331cp-1",
   "0x1.33a400c85af9dp-1",
   "0x1.3feee02d72515p-1",
   "0x1.4c7f26ed1d60fp-1",
   "0x1.59592e296c625p-1",
   "0x1.66819a3a0bf7ap-1",
   "0x1.73fd61d9df542p-1",
   "0x1.81d1d621eb710p-1",
   "0x1.9004ab6d5cc92p-1",
   "0x1.9e9c0346ca836p-1",
   "0x1.ad9e7783fbf1dp-1",
   "0x1.bd1326bb88d10p-1",
   "0x1.cd01c246e405fp-1",
   "0x1.dd729e0bf9cb7p-1",
   "0x1.ee6ec253d2462p-1",
   "0x1.fffffffffffffp-1",
   "0x1.091883bfbf42ep+0",
   "0x1.1286c17acf49cp+0",
   "0x1.1c511a0db83e3p+0",
   "0x1.267e8b3f5da81p+0",
   "0x1.3116c3711527ep+0",
   "0x1.3c2238553dcefp+0",
   "0x1.47aa413b0ee1ep+0",
   "0x1.53b9359d2f918p+0",
   "0x1.605a90c73ab78p+0",
   "0x1.6d9b1b96ce127p+0",
   "0x1.7b891d9a169b3p+0",
   "0x1.8a34971bd700ep+0",
   "0x1.99af8610e4106p+0",
   "0x1.aa0e385c196acp+0",
   "0x1.bb67ae8584ca8p+0",
   "0x1.cdd612dd501f3p+0",
   "0x1.e1774a2562592p+0",
   "0x1.f66da45fee3f0p+0",
   "0x1.06705b35391e7p+1",
   "0x1.127f33e8d12e5p+1",
   "0x1.1f7e220cc4172p+1",
   "0x1.2d8c9200b5686p+1",
   "0x1.3ccfa561175d7p+1",
   "0x1.4d738ef803781p+1",
   "0x1.5fad570f872d7p+1",
   "0x1.73bd2e9a270dfp+1",
   "0x1.89f188bdcd7adp+1",
   "0x1.a2ab4c713671dp+1",
   "0x1.be6398b3f2869p+1",
   "0x1.ddb3d742c2656p+1",
   "0x1.00b0a2833d3c5p+2",
   "0x1.1536e695dda96p+2",
   "0x1.2d18a8e2ff288p+2",
   "0x1.49405f7cc6448p+2",
   "0x1.6af648056a133p+2",
   "0x1.9414813ba6629p+2",
   "0x1.c76237b025ae6p+2",
   "0x1.049e7c666e3fep+3",
   "0x1.3075ac71a38c8p+3",
   "0x1.6dc2fd0bfdbe5p+3",
   "0x1.c99f0ed772d54p+3",
   "0x1.314c55fbc4c58p+4",
   "0x1.ca2e17ec21843p+4",
   "0x1.ca51d76749a49p+5"
  ]
 },
 "gcode_text": {
  "_comment": "Text that goes into G-code comments, in Russian and English. {name} - a ready string from the generator.",
  "generated_by": {
   "ru": "; generated by Calibrate 3D Printer {version} ({title})",
   "en": "; generated by Calibrate 3D Printer {version} ({title})"
  },
  "temp_tower": {
   "ru": "Башня температур {mat} {t0}-{t1}",
   "en": "Temperature tower {mat} {t0}-{t1}"
  },
  "tower_level": {
   "ru": "; ===== уровень {n}: {t} C =====",
   "en": "; ===== level {n}: {t} C ====="
  },
  "pa_lines": {
   "ru": "Линии опережения {mat} {v0}-{v1}",
   "en": "Pressure advance lines {mat} {v0}-{v1}"
  },
  "pa_restore": {
   "ru": " ; подписи - с обычным значением",
   "en": " ; labels with the normal value"
  },
  "flow": {
   "ru": "Поток {mat} {p0}-{p1} %",
   "en": "Flow {mat} {p0}-{p1} %"
  },
  "retraction": {
   "ru": "Откат {mat} {v0}-{v1} мм",
   "en": "Retraction {mat} {v0}-{v1} mm"
  },
  "retraction_level": {
   "ru": "; ===== уровень {n}: откат {v} мм =====",
   "en": "; ===== level {n}: retraction {v} mm ====="
  },
  "max_flow": {
   "ru": "Максимальный расход {mat} {v0}-{v1} мм3/с",
   "en": "Max volumetric flow {mat} {v0}-{v1} mm3/s"
  },
  "overhang": {
   "ru": "Нависания {a0}-{a1}° и мосты {l0}-{l1} мм {mat}",
   "en": "Overhangs {a0}-{a1}° and bridges {l0}-{l1} mm {mat}"
  },
  "first_layer": {
   "ru": "Первый слой {mat}",
   "en": "First layer {mat}"
  },
  "tolerance": {
   "ru": "Зазоры {mat} {g0}-{g1} мм",
   "en": "Tolerances {mat} {g0}-{g1} mm"
  },
  "cube": {
   "ru": "Кубик {s} мм {mat}",
   "en": "Cube {s} mm {mat}"
  },
  "ringing": {
   "ru": "Волны после углов {mat}, разгон {a0}-{a1}",
   "en": "Ringing {mat}, acceleration {a0}-{a1}"
  },
  "ringing_band": {
   "ru": "; ===== пояс {n}: разгон {a} =====",
   "en": "; ===== band {n}: acceleration {a} ====="
  },
  "first_layer_temp_switch": {
   "ru": " ; температура печати после первого слоя",
   "en": " ; print temperature after the first layer"
  }
 },
 "tests": [
  {
   "id": "first_layer",
   "minutes_hint": 11,
   "fast": false,
   "name": {
    "ru": "Первый слой",
    "en": "First layer"
   },
   "look": {
    "ru": "9 квадратов по столу в один слой: везде ровно, без щелей и борозд.",
    "en": "9 single-layer squares over the bed: smooth everywhere, no gaps, no ridges."
   },
   "result": {
    "ru": "Если плохо - чистка и выравнивание стола, Z-смещение.",
    "en": "If not: clean and level the bed, adjust the Z offset."
   },
   "helper": null,
   "params": []
  },
  {
   "id": "temp_tower",
   "minutes_hint": 75,
   "fast": false,
   "name": {
    "ru": "Башня температур",
    "en": "Temperature tower"
   },
   "look": {
    "ru": "Уровень с меньше всего нитей, без провиса моста, с гладкими стенками. Температура выдавлена на передней грани.",
    "en": "The level with the fewest strings, no sagging bridge and smooth walls. The temperature is embossed on the front face."
   },
   "result": {
    "ru": "«Температура сопла» в профиле пластика.",
    "en": "\"Nozzle temperature\" in the filament profile."
   },
   "helper": {
    "kind": "temp",
    "input": {
     "ru": "Лучший уровень (число на грани), °C",
     "en": "Best level (number on the face), °C"
    }
   },
   "params": [
    {
     "key": "t_start",
     "type": "int",
     "min": 150,
     "max": 350,
     "step": 5,
     "label": {
      "ru": "Внизу, °C",
      "en": "Bottom, °C"
     }
    },
    {
     "key": "t_end",
     "type": "int",
     "min": 150,
     "max": 350,
     "step": 5,
     "label": {
      "ru": "Вверху, °C",
      "en": "Top, °C"
     }
    },
    {
     "key": "t_step",
     "type": "int",
     "min": 1,
     "max": 20,
     "step": 1,
     "label": {
      "ru": "Шаг, °C",
      "en": "Step, °C"
     }
    }
   ]
  },
  {
   "id": "flow",
   "minutes_hint": 19,
   "fast": false,
   "name": {
    "ru": "Поток",
    "en": "Flow"
   },
   "look": {
    "ru": "Плашка с самым гладким верхом: без щелей (мало) и бугров (много).",
    "en": "The plate with the smoothest top: no gaps (too little) and no bumps (too much)."
   },
   "result": {
    "ru": "«Коэффициент потока» × число / 100.",
    "en": "\"Flow ratio\" × number / 100."
   },
   "helper": {
    "kind": "flow",
    "input": {
     "ru": "Лучшая плашка (число под ней), %",
     "en": "Best plate (number below it), %"
    }
   },
   "params": [
    {
     "key": "f_start",
     "type": "int",
     "min": 50,
     "max": 120,
     "step": 1,
     "label": {
      "ru": "Первая плашка, %",
      "en": "First plate, %"
     }
    },
    {
     "key": "f_step",
     "type": "int",
     "min": 1,
     "max": 10,
     "step": 1,
     "label": {
      "ru": "Шаг, %",
      "en": "Step, %"
     }
    }
   ]
  },
  {
   "id": "pressure_advance",
   "minutes_hint": 7,
   "fast": false,
   "name": {
    "ru": "Pressure advance",
    "en": "Pressure advance"
   },
   "look": {
    "ru": "Линия ровной толщины на переходах медленно-быстро. Подпись в тысячных: 025 = 0.025.",
    "en": "The line of even width at the slow-fast transitions. Label in thousandths: 025 = 0.025."
   },
   "result": {
    "ru": "«Pressure advance» (Klipper), «K» Linear Advance (Marlin), M572 (RRF).",
    "en": "\"Pressure advance\" (Klipper), Linear Advance \"K\" (Marlin), M572 (RRF)."
   },
   "helper": {
    "kind": "pa",
    "input": {
     "ru": "Лучшая линия (подпись справа)",
     "en": "Best line (label on the right)"
    }
   },
   "params": [
    {
     "key": "pa_start",
     "type": "num",
     "min": 0,
     "max": 1.5,
     "step": 0.005,
     "label": {
      "ru": "От",
      "en": "From"
     },
     "digits": 3
    },
    {
     "key": "pa_end",
     "type": "num",
     "min": 0.005,
     "max": 2,
     "step": 0.005,
     "label": {
      "ru": "До",
      "en": "To"
     },
     "digits": 3
    },
    {
     "key": "pa_step",
     "type": "num",
     "min": 0.001,
     "max": 0.1,
     "step": 0.001,
     "label": {
      "ru": "Шаг",
      "en": "Step"
     },
     "digits": 3
    }
   ]
  },
  {
   "id": "retraction",
   "minutes_hint": 32,
   "fast": false,
   "name": {
    "ru": "Откат",
    "en": "Retraction"
   },
   "look": {
    "ru": "Наименьший откат без нитей между колоннами. Подпись в десятых мм: 08 = 0.8.",
    "en": "The smallest retraction with no strings between the columns. Label in tenths of mm: 08 = 0.8."
   },
   "result": {
    "ru": "«Длина отката» в профиле принтера.",
    "en": "\"Retraction length\" in the printer profile."
   },
   "helper": {
    "kind": "retraction",
    "input": {
     "ru": "Лучший уровень (подпись на колонне)",
     "en": "Best level (label on the column)"
    }
   },
   "params": [
    {
     "key": "r_start",
     "type": "num",
     "min": 0.1,
     "max": 10,
     "step": 0.1,
     "label": {
      "ru": "Первый уровень, мм",
      "en": "First level, mm"
     },
     "digits": 2
    },
    {
     "key": "r_step",
     "type": "num",
     "min": 0.05,
     "max": 2,
     "step": 0.05,
     "label": {
      "ru": "Шаг, мм",
      "en": "Step, mm"
     },
     "digits": 2
    },
    {
     "key": "r_count",
     "type": "int",
     "min": 2,
     "max": 12,
     "step": 1,
     "label": {
      "ru": "Уровней",
      "en": "Levels"
     }
    }
   ]
  },
  {
   "id": "max_flow",
   "minutes_hint": 11,
   "fast": true,
   "name": {
    "ru": "Максимальный расход",
    "en": "Max volumetric flow"
   },
   "look": {
    "ru": "Высота, где стенка стала рваной или защёлкал экструдер; цифры на стенке - мм³/с.",
    "en": "The height where the wall turns rough or the extruder clicks; numbers on the wall are mm³/s."
   },
   "result": {
    "ru": "«Макс. объёмная скорость» = 80-90 % от предела.",
    "en": "\"Max volumetric speed\" = 80-90 % of the limit."
   },
   "helper": {
    "kind": "max_flow",
    "input": {
     "ru": "Предел, мм³/с (цифра на стенке)",
     "en": "Limit, mm³/s (number on the wall)"
    }
   },
   "params": [
    {
     "key": "v_start",
     "type": "num",
     "min": 0.5,
     "max": 60,
     "step": 0.5,
     "label": {
      "ru": "Внизу, мм³/с",
      "en": "Bottom, mm³/s"
     },
     "digits": 1
    },
    {
     "key": "v_end",
     "type": "num",
     "min": 2,
     "max": 80,
     "step": 0.5,
     "label": {
      "ru": "Вверху, мм³/с",
      "en": "Top, mm³/s"
     },
     "digits": 1
    }
   ]
  },
  {
   "id": "overhang_bridge",
   "minutes_hint": 56,
   "fast": false,
   "name": {
    "ru": "Нависания и мосты",
    "en": "Overhangs and bridges"
   },
   "look": {
    "ru": "Наибольший угол нависания без провиса (подписи 20-80° от вертикали); самый длинный ровный мост.",
    "en": "The largest overhang angle without sagging (labels 20-80° from vertical); the longest clean bridge."
   },
   "result": {
    "ru": "Где нужны поддержки.",
    "en": "Where supports are needed."
   },
   "helper": {
    "kind": "overhang",
    "input": {
     "ru": "Наибольший ровный угол, °",
     "en": "Largest clean angle, °"
    }
   },
   "params": []
  },
  {
   "id": "ringing",
   "minutes_hint": 32,
   "fast": true,
   "name": {
    "ru": "Рябь (разгон)",
    "en": "Ringing (acceleration)"
   },
   "look": {
    "ru": "Пояс, с которого после углов появилась рябь. Номер пояса на передней стенке.",
    "en": "The band where ripples appear after the corners. The band number is on the front wall."
   },
   "result": {
    "ru": "Разгон наружных стенок - на пояс ниже.",
    "en": "Outer wall acceleration - one band lower."
   },
   "helper": {
    "kind": "ringing",
    "input": {
     "ru": "Номер пояса, где появилась рябь",
     "en": "Band number where ringing starts"
    }
   },
   "params": [
    {
     "key": "a_start",
     "type": "int",
     "min": 100,
     "max": 50000,
     "step": 100,
     "label": {
      "ru": "Первый пояс, мм/с²",
      "en": "First band, mm/s²"
     }
    },
    {
     "key": "a_step",
     "type": "int",
     "min": 100,
     "max": 10000,
     "step": 100,
     "label": {
      "ru": "Шаг, мм/с²",
      "en": "Step, mm/s²"
     }
    },
    {
     "key": "a_count",
     "type": "int",
     "min": 2,
     "max": 16,
     "step": 1,
     "label": {
      "ru": "Поясов",
      "en": "Bands"
     }
    }
   ]
  },
  {
   "id": "tolerance",
   "minutes_hint": 45,
   "fast": false,
   "name": {
    "ru": "Зазоры",
    "en": "Tolerances"
   },
   "look": {
    "ru": "Наименьший зазор, где штырь выходит из рамки. Подпись в сотых мм: 15 = 0.15.",
    "en": "The smallest gap where the peg comes out of its frame. Label in hundredths of mm: 15 = 0.15."
   },
   "result": {
    "ru": "Зазор для подвижных и вставных деталей.",
    "en": "Clearance for moving and press-fit parts."
   },
   "helper": {
    "kind": "tolerance",
    "input": {
     "ru": "Наименьший рабочий зазор (подпись)",
     "en": "Smallest working gap (label)"
    }
   },
   "params": [
    {
     "key": "gaps",
     "type": "list",
     "min": 0.02,
     "max": 1.0,
     "step": 0.01,
     "label": {
      "ru": "Зазоры, мм (через пробел)",
      "en": "Gaps, mm (space separated)"
     },
     "digits": 2
    }
   ]
  },
  {
   "id": "cube",
   "minutes_hint": 18,
   "fast": false,
   "name": {
    "ru": "Кубик",
    "en": "Cube"
   },
   "look": {
    "ru": "Размеры по X, Y, Z штангенциркулем (передняя грань - с числом).",
    "en": "Measure X, Y, Z with calipers (the front face has the number)."
   },
   "result": {
    "ru": "Все стороны одинаково меньше или больше - поток или усадка; одна ось - натяжение её ремня.",
    "en": "All sides equally off - flow or shrinkage; one axis only - that axis' belt tension."
   },
   "helper": {
    "kind": "cube",
    "input": {
     "ru": "Измерено X Y Z, мм",
     "en": "Measured X Y Z, mm"
    }
   },
   "params": [
    {
     "key": "size",
     "type": "int",
     "min": 10,
     "max": 40,
     "step": 1,
     "label": {
      "ru": "Размер, мм",
      "en": "Size, mm"
     }
    }
   ]
  }
 ],
 "ui_text": {
  "_comment": "Made by tools/make_ui_text.py. Interface strings, Russian and English.",
  "app_title": {
   "ru": "Калибровка 3D-принтера",
   "en": "Calibrate 3D Printer"
  },
  "app_sub": {
   "ru": "Готовые калибровочные G-code для любого FDM-принтера, без слайсера",
   "en": "Ready calibration G-code for any FDM printer, no slicer needed"
  },
  "theme": {
   "ru": "Тема",
   "en": "Theme"
  },
  "language": {
   "ru": "Язык",
   "en": "Language"
  },
  "theme_glass": {
   "ru": "Стеклянная",
   "en": "Glass"
  },
  "theme_formal": {
   "ru": "Строгая",
   "en": "Formal"
  },
  "theme_light": {
   "ru": "Светлая",
   "en": "Light"
  },
  "theme_night": {
   "ru": "Ночная",
   "en": "Night"
  },
  "theme_warm": {
   "ru": "Тёплая",
   "en": "Warm"
  },
  "step_printer": {
   "ru": "1. Принтер",
   "en": "1. Printer"
  },
  "step_material": {
   "ru": "2. Пластик",
   "en": "2. Material"
  },
  "step_tests": {
   "ru": "3. Тесты",
   "en": "3. Tests"
  },
  "step_download": {
   "ru": "4. Скачать",
   "en": "4. Download"
  },
  "step_results": {
   "ru": "Результаты",
   "en": "Results"
  },
  "next": {
   "ru": "Дальше",
   "en": "Next"
  },
  "back": {
   "ru": "Назад",
   "en": "Back"
  },
  "import_title": {
   "ru": "Загрузить свой G-code",
   "en": "Load your G-code"
  },
  "import_hint": {
   "ru": "Выберите файл, который ваш принтер уже хорошо напечатал. Программа возьмёт из него начальный и конечный код, стол, сопло, пруток, прошивку и температуры.",
   "en": "Pick a file your printer has already printed well. The program takes the start and end code, bed, nozzle, filament, firmware and temperatures from it."
  },
  "import_button": {
   "ru": "Выбрать G-code…",
   "en": "Choose G-code…"
  },
  "import_done": {
   "ru": "Импортировано из {file} ({slicer}).",
   "en": "Imported from {file} ({slicer})."
  },
  "import_replaced": {
   "ru": "Заменено подстановками: {n}",
   "en": "Replaced with placeholders: {n}"
  },
  "import_missing": {
   "ru": "Не найдено, заполните сами: {fields}",
   "en": "Not found, fill in yourself: {fields}"
  },
  "import_all_found": {
   "ru": "Найдено всё нужное.",
   "en": "Everything needed was found."
  },
  "import_bambu": {
   "ru": "Bambu Lab: у прошивки свой диалект G-code. Непроверено - первую печать под присмотром.",
   "en": "Bambu Lab: the firmware has its own G-code dialect. Not checked - watch the first print."
  },
  "import_fw_unknown": {
   "ru": "Прошивку определить не удалось - выберите её сами.",
   "en": "Could not tell the firmware - choose it yourself."
  },
  "import_failed": {
   "ru": "Не удалось прочитать файл: {error}",
   "en": "Could not read the file: {error}"
  },
  "profile": {
   "ru": "Профиль",
   "en": "Profile"
  },
  "verified": {
   "ru": "проверен на принтере",
   "en": "checked on a real printer"
  },
  "unverified": {
   "ru": "непроверено",
   "en": "not checked"
  },
  "unverified_hint": {
   "ru": "Этот профиль не проверен на настоящем принтере. Проверьте его импортом своего G-code.",
   "en": "This profile was not checked on a real printer. Check it by importing your own G-code."
  },
  "my_profile": {
   "ru": "мой",
   "en": "mine"
  },
  "name": {
   "ru": "Название",
   "en": "Name"
  },
  "prefix": {
   "ru": "Префикс файлов",
   "en": "File prefix"
  },
  "bed_x": {
   "ru": "Стол X, мм",
   "en": "Bed X, mm"
  },
  "bed_y": {
   "ru": "Стол Y, мм",
   "en": "Bed Y, mm"
  },
  "bed_z": {
   "ru": "Высота Z, мм",
   "en": "Height Z, mm"
  },
  "origin": {
   "ru": "Начало координат",
   "en": "Origin"
  },
  "origin_corner": {
   "ru": "угол",
   "en": "corner"
  },
  "origin_center": {
   "ru": "центр",
   "en": "centre"
  },
  "shape": {
   "ru": "Форма стола",
   "en": "Bed shape"
  },
  "shape_rect": {
   "ru": "прямоугольник",
   "en": "rectangle"
  },
  "shape_round": {
   "ru": "круг",
   "en": "round"
  },
  "nozzle": {
   "ru": "Сопло, мм",
   "en": "Nozzle, mm"
  },
  "filament": {
   "ru": "Пруток, мм",
   "en": "Filament, mm"
  },
  "firmware": {
   "ru": "Прошивка",
   "en": "Firmware"
  },
  "max_speed": {
   "ru": "Макс. скорость, мм/с",
   "en": "Max speed, mm/s"
  },
  "max_accel": {
   "ru": "Макс. разгон, мм/с²",
   "en": "Max acceleration, mm/s²"
  },
  "default_accel": {
   "ru": "Обычный разгон, мм/с²",
   "en": "Default acceleration, mm/s²"
  },
  "travel_speed": {
   "ru": "Переезды, мм/с",
   "en": "Travel, mm/s"
  },
  "z_speed": {
   "ru": "Скорость Z, мм/с",
   "en": "Z speed, mm/s"
  },
  "retract_length": {
   "ru": "Откат, мм",
   "en": "Retraction, mm"
  },
  "retract_speed": {
   "ru": "Скорость отката, мм/с",
   "en": "Retraction speed, mm/s"
  },
  "z_hop": {
   "ru": "Подъём Z, мм",
   "en": "Z hop, mm"
  },
  "opt_canvas": {
   "ru": "Подача CANVAS (M6211)",
   "en": "CANVAS feeder (M6211)"
  },
  "opt_nozzle_wipe": {
   "ru": "Чистка сопла (M729)",
   "en": "Nozzle wipe (M729)"
  },
  "start_code": {
   "ru": "Начальный код",
   "en": "Start code"
  },
  "end_code": {
   "ru": "Конечный код",
   "en": "End code"
  },
  "placeholders_hint": {
   "ru": "Подстановки: {nozzle_temp} {first_layer_nozzle_temp} {bed_temp} {max_z} {max_z_plus_50_capped} {filament_type} {layer_height} {print_title} {total_layers}; строка с {?флаг} - по условию.",
   "en": "Placeholders: {nozzle_temp} {first_layer_nozzle_temp} {bed_temp} {max_z} {max_z_plus_50_capped} {filament_type} {layer_height} {print_title} {total_layers}; a line starting with {?flag} is conditional."
  },
  "save_profile": {
   "ru": "Сохранить как свой",
   "en": "Save as mine"
  },
  "delete_profile": {
   "ru": "Удалить свой",
   "en": "Delete mine"
  },
  "export_json": {
   "ru": "Экспорт JSON",
   "en": "Export JSON"
  },
  "import_json": {
   "ru": "Импорт JSON",
   "en": "Import JSON"
  },
  "saved": {
   "ru": "Сохранено: {name}",
   "en": "Saved: {name}"
  },
  "profile_errors": {
   "ru": "Ошибки профиля: {errors}",
   "en": "Profile errors: {errors}"
  },
  "section_bed": {
   "ru": "Стол и механика",
   "en": "Bed and motion"
  },
  "section_code": {
   "ru": "Начальный и конечный код",
   "en": "Start and end code"
  },
  "source": {
   "ru": "Источник",
   "en": "Source"
  },
  "material": {
   "ru": "Пластик",
   "en": "Material"
  },
  "mat_generic": {
   "ru": "общие значения",
   "en": "generic values"
  },
  "mat_verified": {
   "ru": "проверенные настройки",
   "en": "tested settings"
  },
  "mat_type": {
   "ru": "Тип",
   "en": "Type"
  },
  "tower_start": {
   "ru": "Башня: внизу, °C",
   "en": "Tower: bottom, °C"
  },
  "tower_end": {
   "ru": "Башня: вверху, °C",
   "en": "Tower: top, °C"
  },
  "tower_step": {
   "ru": "Башня: шаг, °C",
   "en": "Tower: step, °C"
  },
  "nozzle_temp": {
   "ru": "Сопло, °C",
   "en": "Nozzle, °C"
  },
  "first_layer_temp": {
   "ru": "Сопло, первый слой, °C",
   "en": "Nozzle, first layer, °C"
  },
  "bed_temp": {
   "ru": "Стол, °C",
   "en": "Bed, °C"
  },
  "flow": {
   "ru": "Поток",
   "en": "Flow ratio"
  },
  "mvs": {
   "ru": "Макс. расход, мм³/с",
   "en": "Max flow, mm³/s"
  },
  "fan": {
   "ru": "Вентилятор, 0-1",
   "en": "Fan, 0-1"
  },
  "bridge_fan": {
   "ru": "Вентилятор на мостах, 0-1",
   "en": "Bridge fan, 0-1"
  },
  "fan_off_layers": {
   "ru": "Слоёв без вентилятора",
   "en": "Layers without fan"
  },
  "min_layer_time": {
   "ru": "Мин. время слоя, с",
   "en": "Min layer time, s"
  },
  "pa_default": {
   "ru": "Pressure advance",
   "en": "Pressure advance"
  },
  "density": {
   "ru": "Плотность, г/см³",
   "en": "Density, g/cm³"
  },
  "max_flow_from": {
   "ru": "Тест расхода: от, мм³/с",
   "en": "Flow test: from, mm³/s"
  },
  "max_flow_to": {
   "ru": "Тест расхода: до, мм³/с",
   "en": "Flow test: to, mm³/s"
  },
  "tests_hint": {
   "ru": "Отметьте тесты. У каждого - предпросмотр, время и граммы.",
   "en": "Tick the tests. Each has a preview, time and grams."
  },
  "select_all": {
   "ru": "Все",
   "en": "All"
  },
  "select_none": {
   "ru": "Ни одного",
   "en": "None"
  },
  "minutes": {
   "ru": "мин",
   "en": "min"
  },
  "grams": {
   "ru": "г",
   "en": "g"
  },
  "time_grams": {
   "ru": "~{time}, ~{grams} г",
   "en": "~{time}, ~{grams} g"
  },
  "hours_minutes": {
   "ru": "{h} ч {m} мин",
   "en": "{h} h {m} min"
  },
  "only_minutes": {
   "ru": "{m} мин",
   "en": "{m} min"
  },
  "look_for": {
   "ru": "Что искать",
   "en": "What to look for"
  },
  "result_where": {
   "ru": "Куда результат",
   "en": "Where the result goes"
  },
  "params": {
   "ru": "Параметры",
   "en": "Parameters"
  },
  "preview_top": {
   "ru": "Вид сверху",
   "en": "Top view"
  },
  "preview_front": {
   "ru": "Вид спереди",
   "en": "Front view"
  },
  "preview_3d": {
   "ru": "3D",
   "en": "3D"
  },
  "layer_upto": {
   "ru": "До слоя",
   "en": "Up to layer"
  },
  "fast_warning": {
   "ru": "Печатается нарочно быстро: следите за первыми минутами и остановите, если экструдер сильно щёлкает.",
   "en": "Printed fast on purpose: watch the first minutes and stop if the extruder clicks hard."
  },
  "computing": {
   "ru": "Считаю…",
   "en": "Computing…"
  },
  "gen_error": {
   "ru": "Ошибка: {error}",
   "en": "Error: {error}"
  },
  "does_not_fit": {
   "ru": "Не помещается на стол",
   "en": "Does not fit the bed"
  },
  "check_failed": {
   "ru": "Проверка G-code: {problems}",
   "en": "G-code check: {problems}"
  },
  "check_ok": {
   "ru": "Проверка G-code пройдена",
   "en": "G-code check passed"
  },
  "download_hint": {
   "ru": "Файлы для выбранных тестов. Имена: <префикс>_<сопло>_<тест>_<пластик>_<диапазон>.gcode",
   "en": "Files for the selected tests. Names: <prefix>_<nozzle>_<test>_<material>_<range>.gcode"
  },
  "save_folder": {
   "ru": "Сохранить в папку…",
   "en": "Save to folder…"
  },
  "save_zip": {
   "ru": "Сохранить архивом (zip)…",
   "en": "Save as zip…"
  },
  "download_one": {
   "ru": "Скачать",
   "en": "Download"
  },
  "download_zip": {
   "ru": "Скачать все (zip)",
   "en": "Download all (zip)"
  },
  "saved_files": {
   "ru": "Сохранено файлов: {n} в {path}",
   "en": "Saved {n} files to {path}"
  },
  "nothing_selected": {
   "ru": "Не выбрано ни одного теста.",
   "en": "No test selected."
  },
  "print_order": {
   "ru": "Порядок печати",
   "en": "Print order"
  },
  "col_n": {
   "ru": "№",
   "en": "#"
  },
  "col_test": {
   "ru": "Тест",
   "en": "Test"
  },
  "col_file": {
   "ru": "Файл",
   "en": "File"
  },
  "col_time": {
   "ru": "Время",
   "en": "Time"
  },
  "col_look": {
   "ru": "Что ищем",
   "en": "What to look for"
  },
  "col_result": {
   "ru": "Куда результат",
   "en": "Where it goes"
  },
  "total": {
   "ru": "Всего: {n} файлов, ~{time}, ~{grams} г",
   "en": "Total: {n} files, ~{time}, ~{grams} g"
  },
  "watch_first": {
   "ru": "G-code проверен расчётом, а не на вашем принтере: первую печать каждого теста - под присмотром.",
   "en": "The G-code is checked by calculation, not on your printer: watch the first print of each test."
  },
  "results_hint": {
   "ru": "Напечатали тест? Впишите лучший уровень или линию - программа даст число для профиля слайсера.",
   "en": "Printed a test? Enter the best level or line - the program gives the number for your slicer profile."
  },
  "helper_input": {
   "ru": "Ваш ответ",
   "en": "Your answer"
  },
  "helper_temp": {
   "ru": "«Температура сопла» в профиле пластика: {value} °C",
   "en": "\"Nozzle temperature\" in the filament profile: {value} °C"
  },
  "helper_flow": {
   "ru": "«Коэффициент потока» в профиле пластика: {value}",
   "en": "\"Flow ratio\" in the filament profile: {value}"
  },
  "helper_pa": {
   "ru": "«Pressure advance» (Klipper) / K (Marlin) / M572 (RRF): {value}",
   "en": "\"Pressure advance\" (Klipper) / K (Marlin) / M572 (RRF): {value}"
  },
  "helper_retraction": {
   "ru": "«Длина отката» в профиле принтера: {value} мм",
   "en": "\"Retraction length\" in the printer profile: {value} mm"
  },
  "helper_max_flow": {
   "ru": "«Макс. объёмная скорость» в профиле пластика: {value} мм³/с (85 % от предела)",
   "en": "\"Max volumetric speed\" in the filament profile: {value} mm³/s (85 % of the limit)"
  },
  "helper_overhang": {
   "ru": "Поддержки нужны для нависаний положе: порог поддержек {value}° от горизонтали",
   "en": "Supports are needed for flatter overhangs: support threshold {value}° from horizontal"
  },
  "helper_ringing": {
   "ru": "«Разгон наружных стенок»: {value} мм/с²",
   "en": "\"Outer wall acceleration\": {value} mm/s²"
  },
  "helper_ringing_first": {
   "ru": "Рябь уже на первом поясе: попробуйте {value} мм/с² и проверьте натяжение ремней",
   "en": "Ringing already in the first band: try {value} mm/s² and check belt tension"
  },
  "helper_tolerance": {
   "ru": "Зазор для подвижных и вставных деталей: {value} мм",
   "en": "Clearance for moving and press-fit parts: {value} mm"
  },
  "helper_cube_ok": {
   "ru": "Размеры в пределах 0.1 мм - всё в порядке",
   "en": "Sizes within 0.1 mm - all good"
  },
  "helper_cube_flow": {
   "ru": "X и Y одинаково отличаются: поток или усадка. Попробуйте коэффициент потока {value}",
   "en": "X and Y are off the same way: flow or shrinkage. Try flow ratio {value}"
  },
  "helper_cube_axis": {
   "ru": "Отличается только ось {value}: проверьте натяжение ремня этой оси",
   "en": "Only axis {value} is off: check that axis' belt tension"
  },
  "need_number": {
   "ru": "Впишите число",
   "en": "Enter a number"
  },
  "need_three": {
   "ru": "Впишите три числа: X Y Z",
   "en": "Enter three numbers: X Y Z"
  },
  "out_of_range": {
   "ru": "Такого уровня в тесте нет",
   "en": "The test has no such level"
  },
  "no_helper": {
   "ru": "Для этого теста число не нужно - смотрите подсказку",
   "en": "No number for this test - see the hint"
  },
  "about": {
   "ru": "О программе",
   "en": "About"
  },
  "version": {
   "ru": "Версия {v}",
   "en": "Version {v}"
  },
  "offline": {
   "ru": "Всё работает без сети, ничего никуда не отправляется.",
   "en": "Works offline, nothing is sent anywhere."
  }
 }
};
  if (typeof module === 'object' && module.exports) module.exports = C3D.data;
})();
