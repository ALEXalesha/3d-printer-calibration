;FLAVOR:Marlin
;TIME:612
;Filament used: 0.5m
;Layer height: 0.2
;MINX:100
;MINY:100
;MINZ:0.2
;MAXX:120
;MAXY:120
;MAXZ:0.4
;TARGET_MACHINE.NAME:Creality Ender-3
;Generated with Cura_SteamEngine 5.8.0
M140 S60
M105
M190 S60
M104 S200
M105
M109 S200
M82 ;absolute extrusion mode
G28 ;Home
G92 E0
G1 Z2.0 F3000
G1 X0.1 Y20 Z0.3 F5000.0
G1 X0.1 Y200.0 Z0.3 F1500.0 E15
G92 E0
G1 Z2.0 F3000
;LAYER_COUNT:2
;LAYER:0
M107
G1 X100 Y100 F6000
G1 X120 Y100 E0.8 F1200
;LAYER:1
G1 X120 Y120 E1.6 F1200
;TIME_ELAPSED:612.0
G1 F2700 E-5
M140 S0
M104 S0
G1 X0 Y220
M84 X Y E
M82 ;absolute extrusion mode
M104 S0
;End of Gcode
;SETTING_3 {"global_quality": "[general]\\nversion = 4\\nname = Standard\\n[values]\\nadhes
;SETTING_3 ion_type = skirt\\nlayer_height = 0.2\\nretraction_amount = 5\\nretraction_speed = 45\\n"
;SETTING_3 ,"extruder_quality": ["[general]\\nversion = 4\\n[values]\\nmaterial_print_temperatur
;SETTING_3 e = 200\\nmaterial_bed_temperature = 60\\n"]}
