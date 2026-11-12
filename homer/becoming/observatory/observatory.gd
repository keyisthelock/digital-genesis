extends Control
## Read-only observer. This process has no simulation command channel.

const BG := Color("#0E161D")
const PANEL := Color("#17242D")
const LINE := Color("#3A515D")
const WHITE := Color("#E6EFF2")
const MUTED := Color("#A6BAC2")
const TEAL := Color("#88E5CD")
const AMBER := Color("#FFC58A")
const REGIONS := {
	"motor": [Rect2(105, 234, 186, 60), "Native motor", "Preserved for embodied tasks.", "Education has no motor authority."],
	"language": [Rect2(414, 196, 186, 60), "Language", "Local Qwen selected dialogue evidence", "or generated a labeled interpretation."],
	"memory": [Rect2(129, 365, 186, 60), "Episodic memory", "SQLite recorded a simulator outcome.", "The private record stays out of this feed."],
	"retrieval": [Rect2(429, 345, 186, 60), "Semantic retrieval", "Retrieval queries the life journal.", "Local keyword search is the default."],
	"appraisal": [Rect2(302, 435, 186, 60), "Appraisal", "Functional tags annotate observations.", "They carry no authority over motor actions."],
	"executive": [Rect2(262, 295, 211, 60), "Goal manager", "Selects a permitted task and logs why.", "The verifier scores the answer separately."]
}
const LINKS := [["motor","executive"],["language","executive"],["memory","executive"],
	["memory","retrieval"],["retrieval","language"],["appraisal","executive"]]
const CHAPTERS := ["The Archive", "The Academy", "The Forge", "The Citadel", "The Open Horizon"]

var feed := ""
var raw := ""
var records: Array[Dictionary] = []
var cursor := 0
var selected := "executive"
var following := true


func _ready() -> void:
	focus_mode = Control.FOCUS_ALL
	grab_focus()
	var args := OS.get_cmdline_user_args()
	if not args.is_empty():
		feed = args[0]
	load_feed()
	if "--verify" in args:
		if records.is_empty() or records.all(func(row): return row.get("research", {}).get("kind") != "learning"):
			push_error("No learning record in observer input")
			get_tree().quit(1)
		else:
			print("Observatory verified ", records.size(), " frames, origin=", records.back().get("origin"))
			get_tree().quit()
		return
	var timer := Timer.new()
	timer.wait_time = 0.5
	timer.timeout.connect(load_feed)
	add_child(timer)
	timer.start()
	if "--capture" in args:
		var index := args.find("--capture")
		if index+1 < args.size():
			await RenderingServer.frame_post_draw
			await RenderingServer.frame_post_draw
			var error := get_viewport().get_texture().get_image().save_png(args[index+1])
			get_tree().quit(0 if error == OK else 1)


func load_feed() -> void:
	if feed.is_empty() or not FileAccess.file_exists(feed):
		queue_redraw()
		return
	var content := FileAccess.get_file_as_string(feed)
	if content == raw:
		return
	raw = content
	records.clear()
	for line in content.split("\n", false):
		var row: Variant = JSON.parse_string(line)
		if row is Dictionary:
			records.append(row)
	cursor = maxi(0, records.size()-1) if following else mini(cursor,maxi(0,records.size()-1))
	queue_redraw()


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		for key in REGIONS:
			if REGIONS[key][0].has_point(event.position):
				selected = key
				queue_redraw()
				return
	if event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_1, KEY_2, KEY_3, KEY_4, KEY_5:
				var chapter: String = CHAPTERS[int(event.keycode)-KEY_1]
				for index in range(records.size()):
					if records[index].get("mode") == chapter:
						cursor = index
						following = false
						break
			KEY_LEFT:
				following = false
				cursor = maxi(0, cursor-1)
			KEY_RIGHT:
				following = false
				cursor = mini(maxi(0,records.size()-1), cursor+1)
			KEY_SPACE:
				following = not following
				if following:
					cursor = maxi(0,records.size()-1)
			_:
				return
		queue_redraw()


func label_at(at: Vector2, value: String, font_size: int, ink: Color = WHITE) -> void:
	draw_string(ThemeDB.fallback_font, at, value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, ink)


func card(rect: Rect2, fill: Color, border: Color) -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = fill
	style.border_color = border
	style.set_border_width_all(1)
	style.set_corner_radius_all(12)
	draw_style_box(style, rect)


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BG)
	label_at(Vector2(45,55), "HOMER-01", 34)
	label_at(Vector2(46,84), "Learning Observatory", 19, MUTED)
	label_at(Vector2(873,53), "DIGITAL GENESIS  /  1.8", 15, TEAL)
	var row: Dictionary = records[cursor] if not records.is_empty() else {}
	var active: Array = row.get("active", [])
	card(Rect2(45,117,645,430), PANEL, LINE)
	card(Rect2(711,117,364,430), PANEL, LINE)
	label_at(Vector2(68,150), "FUNCTIONAL MAP", 14, TEAL)
	label_at(Vector2(733,150), "DECISION INSPECTOR", 14, TEAL)
	var contour := PackedVector2Array([
		Vector2(150,208),Vector2(220,179),Vector2(308,180),Vector2(352,192),Vector2(423,174),
		Vector2(514,174),Vector2(592,202),Vector2(635,246),Vector2(646,304),Vector2(629,364),
		Vector2(585,425),Vector2(509,463),Vector2(466,512),Vector2(371,518),Vector2(311,473),
		Vector2(239,472),Vector2(159,438),Vector2(100,389),Vector2(83,328),Vector2(92,261),
		Vector2(150,208)])
	draw_colored_polygon(contour, Color("#1B3039"))
	draw_polyline(contour, LINE, 2.0, true)
	for link in LINKS:
		var hot := active.has(link[0]) and active.has(link[1])
		draw_line(REGIONS[link[0]][0].get_center(),REGIONS[link[1]][0].get_center(),
			TEAL if hot else LINE, 2.5 if hot else 1.5, true)
	for key in REGIONS:
		var rect: Rect2 = REGIONS[key][0]
		var hot := active.has(key)
		card(rect, Color("#23453F") if hot else BG, TEAL if hot else (MUTED if key==selected else LINE))
		draw_circle(rect.position+Vector2(17,29), 4, TEAL if hot else LINE)
		label_at(rect.position+Vector2(29,35),REGIONS[key][1],16, WHITE if hot else MUTED)
	label_at(Vector2(733,195), str(row.get("caption","Waiting for a decision feed")), 21)
	label_at(Vector2(733,230), "ORIGIN", 12, MUTED)
	label_at(Vector2(733,253), str(row.get("origin","—")), 18, AMBER if row.get("error", false) else TEAL)
	label_at(Vector2(733,284), "Chapter  %s" % row.get("mode","—"), 15)
	label_at(Vector2(733,313), "Attempt  %d" % int(row.get("tick", 0)), 15)
	label_at(Vector2(733,343), "Cited memories  %d" % int(row.get("retrieved_count",0)), 15)
	draw_line(Vector2(733,369),Vector2(1052,369),LINE)
	var research: Dictionary = row.get("research", {})
	if research.is_empty():
		label_at(Vector2(733,401), REGIONS[selected][1], 18, TEAL)
		label_at(Vector2(733,432), REGIONS[selected][2], 14, MUTED)
		label_at(Vector2(733,455), REGIONS[selected][3], 14, MUTED)
	else:
		label_at(Vector2(733,391), str(research.get("goal","")).left(49), 13, TEAL)
		label_at(Vector2(733,415), "Domain  %s" % research.get("observation",""), 13)
		label_at(Vector2(733,437), "Verifier  %s" % research.get("outcome",""), 13)
		label_at(Vector2(733,481), "Memory refs  %s" % research.get("refs","None"), 13, MUTED)
		label_at(Vector2(733,503), "Plan  %s" % research.get("consequence",""), 13, TEAL)
		label_at(Vector2(68,531), "%s  ·  %s" % [REGIONS[selected][1],REGIONS[selected][2]], 12, MUTED)
	label_at(Vector2(46,585), "← / →  Step through attempts       1–5  Jump to chapter       Space  Follow latest", 15, MUTED)
	label_at(Vector2(46,625), "%s   •   %s / %s decisions" % [
		"LIVE FOLLOW" if following else "REPLAY",cursor+1 if not records.is_empty() else 0,records.size()], 16, TEAL)
	label_at(Vector2(730,625), "Read-only view of recorded subsystem activity", 14, MUTED)
