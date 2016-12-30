from pylab import *
import numpy
import freetype
import os
import subprocess

### shape-specific:
#{
#	"type": "circle",
#	"x": 1.0,
#	"y": 1.0,
#	"radius": 1.0,
#}
#{
#	"type": "rectangle",
#	"x": 1.0,
#	"y": 1.0,
#	"width": 1.0,
#	"height": 1.0,
#	"angle": 1.0,
#}
#{
#	"type": "polygon",
#	"x": array([1.0, 2.0, 3.0]),
#	"y": array([1.0, 1.0, 5.0]),
#	"closed": True,
#}
### for all shapes:
#{
#	"layer": "copper1-top",
#	"outline": None, # should be None or width in mm
#	"hole": False,
#	"order": 0,
#	"pad": False, # relevant only for gerber export
#}

layerstack = {
	"copper1-top"   : {"type": "gerber", "ext": ".gtl"         , "color": (1.0, 0.0, 0.0)},
	"copper1-bot"   : {"type": "gerber", "ext": ".gbl"         , "color": (0.0, 0.0, 1.0)},
	"mask-top"      : {"type": "gerber", "ext": ".gts"         , "color": (0.0, 1.0, 0.0)},
	"mask-bot"      : {"type": "gerber", "ext": ".gbs"         , "color": (0.0, 0.6, 0.0)},
	"silk-top"      : {"type": "gerber", "ext": ".gto"         , "color": (1.0, 1.0, 0.5)},
	"silk-bot"      : {"type": "gerber", "ext": ".gbo"         , "color": (0.6, 0.6, 0.3)},
	"board-outline" : {"type": "gerber", "ext": ".gko"         , "color": (0.2, 0.2, 0.2)},
	"drill-plated"  : {"type": "drill" , "ext": ".txt"         , "color": (0.6, 0.6, 0.6)},
	"courtyard-top" : {"type": None    , "ext": None           , "color": (0.0, 1.0, 0.5)},
	"courtyard-bot" : {"type": None    , "ext": None           , "color": (0.0, 0.6, 0.3)},
	"mech1-top"     : {"type": None    , "ext": None           , "color": (0.5, 0.0, 1.0)},
	"mech1-bot"     : {"type": None    , "ext": None           , "color": (0.3, 0.0, 0.6)},
	"mech2-top"     : {"type": None    , "ext": None           , "color": (1.0, 0.0, 1.0)},
	"mech2-bot"     : {"type": None    , "ext": None           , "color": (0.6, 0.0, 0.6)},
	"mech3-top"     : {"type": None    , "ext": None           , "color": (1.0, 0.0, 0.5)},
	"mech3-bot"     : {"type": None    , "ext": None           , "color": (0.6, 0.0, 0.3)},
}

def bezier1(a, b, t):
	s = 1.0 - t
	return s * a + t * b

def bezier2(a, b, c, t):
	s = 1.0 - t
	return s * s * a + 2 * s * t * b + t * t * c

def bezier3(a, b, c, d, t):
	s = 1.0 - t
	return s * s * (s * a + 3 * t * b) + t * t * (t * d + 3 * s * c)

def polygon_direction(x, y):
	area = 0.0
	for i in range(2, len(x)):
		area += (x[i] - x[0]) * (y[i - 1] - y[0]) - (y[i] - y[0]) * (x[i - 1] - x[0])
	return "cw" if area > 0 else "ccw"

def circle_steps(radius):
	return 360 // 5
	#return max(16, 4 * int(round(pi / arccos(1.0 - 0.005 / radius) / 4)))

def stroke_line(x1, y1, x2, y2, width, endcap1, endcap2):
	angle = arctan2(y2 - y1, x2 - x1) + linspace(-pi / 2, pi / 2, 180 // 5 + 1)
	return array([
		concatenate((x1 - width / 2 * cos(angle), x2 + width / 2 * cos(angle))),
		concatenate((y1 - width / 2 * sin(angle), y2 + width / 2 * sin(angle))),
	]).transpose()

def shape_to_polygon(shape):
	if shape["type"] == "circle":
		angle = linspace(0, 2 * pi, circle_steps(shape["radius"]), endpoint=False)
		return array([
			shape["x"] + shape["radius"] * cos(angle),
			shape["y"] + shape["radius"] * sin(angle),
		]).transpose()
	elif shape["type"] == "rectangle":
		rx = array([-shape["width"]  / 2,  shape["width"]  / 2,  shape["width"]  / 2, -shape["width"]  / 2])
		ry = array([-shape["height"] / 2, -shape["height"] / 2,  shape["height"] / 2,  shape["height"] / 2])
		return array([
			shape["x"] + rx * cos(shape["angle"] * pi / 180) - ry * sin(shape["angle"] * pi / 180),
			shape["y"] + rx * sin(shape["angle"] * pi / 180) + ry * cos(shape["angle"] * pi / 180),
		]).transpose()
	elif shape["type"] == "polygon":
		return array([
			shape["x"],
			shape["y"],
		]).transpose()
	else:
		raise Exception("Unknown shape type!")

def make_circle(layer, x, y, radius, outline=None, hole=False, order=0, pad=False):
	return [{
		"layer": layer,
		"type": "circle",
		"x": x,
		"y": y,
		"radius": radius,
		"outline": outline,
		"hole": hole,
		"order": order,
		"pad": pad,
	}]

def make_rectangle(layer, x, y, width, height, angle=0.0, outline=None, hole=False, order=0, pad=False):
	return [{
		"layer": layer,
		"type": "rectangle",
		"x": x,
		"y": y,
		"width": width,
		"height": height,
		"angle": angle,
		"outline": outline,
		"hole": hole,
		"order": order,
		"pad": pad,
	}]

def make_polygon(layer, x, y, closed=True, outline=None, hole=False, order=0, pad=False):
	return [{
		"layer": layer,
		"type": "polygon",
		"x": array(x),
		"y": array(y),
		"closed": closed,
		"outline": outline,
		"hole": hole,
		"order": order,
		"pad": pad,
	}]

def make_line(layer, x1, y1, x2, y2, closed=False, outline=None, hole=False, order=0):
	return make_polygon(layer, [x1, x2], [y1, y2], closed=closed, outline=outline, hole=hole, order=order)

def make_arc(layer, x, y, radius, angle1, angle2, closed=False, outline=None, hole=False, order=0):
	steps = max(2, 1 + int(round(circle_steps(radius) * abs(angle1 - angle2) / 360.0)))
	angle = linspace(angle1 * pi / 180, angle2 * pi / 180, steps)
	return make_polygon(layer, x + radius * cos(angle), y + radius * sin(angle), closed=closed, outline=outline, hole=hole, order=order)

def make_text(layer, font, text, size, origin_x, origin_y, align="left", valign="baseline", spacing=0.0, order=0):
	
	# load font
	face = freetype.Face(font)
	xscale = size / face.units_per_EM
	yscale = size / face.units_per_EM
	
	# calculate total width
	total_width = 0.0
	
	for ch in range(len(text)):
		face.load_char(text[ch], freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_SCALE)
		if ch != 0:
			kerning = face.get_kerning(text[ch - 1], text[ch], freetype.FT_KERNING_UNSCALED)
			total_width += kerning.x * xscale + spacing
		total_width += face.glyph.advance.x * xscale
	
	# calculate start position
	if align == "left":
		pos_x = origin_x
	elif align == "center":
		pos_x = origin_x - total_width / 2
	elif align == "right":
		pos_x = origin_x - total_width
	else:
		raise Exception("Unknown alignment!")
	if valign == "baseline":
		pos_y = origin_y
	elif valign == "top":
		pos_y = origin_y - face.ascender * yscale
	elif valign == "center":
		pos_y = origin_y - (face.ascender + face.descender) / 2 * yscale
	elif valign == "bottom":
		pos_y = origin_y - face.descender * yscale
	else:
		raise Exception("Unknown alignment!")
	
	# convert to polygons
	shapes = []
	for ch in range(len(text)):
		
		# load one glyph
		face.load_char(text[ch], freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_SCALE)
		outline = face.glyph.outline
		
		# move position
		if ch != 0:
			kerning = face.get_kerning(text[ch - 1], text[ch], freetype.FT_KERNING_UNSCALED)
			pos_x += kerning.x * xscale + spacing
		
		# add polygons
		start = 0
		for contour in outline.contours:
			end = contour + 1
			points = outline.points[start:end]
			tags = outline.tags[start:end]
			start = end
			
			oncurve = [bool((tags[i] >> 0) & 1) for i in range(len(points))]
			thirdorder = [bool((tags[i] >> 1) & 1) for i in range(len(points))]
			hasmode = [bool((tags[i] >> 2) & 1) for i in range(len(points))]
			mode = [(tags[i] >> 5) & 0x7 for i in range(len(points))]
			
			t = (numpy.arange(16) + 1) / 16
			n = len(oncurve)
			px = []
			py = []
			for i in range(len(points)):
				if oncurve[i]:
					if oncurve[i - 1]:
						xx = bezier1(points[i - 1][0], points[i][0], t)
						yy = bezier1(points[i - 1][1], points[i][1], t)
						px.extend(xx)
						py.extend(yy)
				else:
					assert(not thirdorder[i])
					x1 = points[i - 1][0] if oncurve[i - 1] else (points[i][0] + points[i - 1][0]) / 2
					y1 = points[i - 1][1] if oncurve[i - 1] else (points[i][1] + points[i - 1][1]) / 2
					x2 = points[i + 1 - n][0] if oncurve[i + 1 - n] else (points[i][0] + points[i + 1 - n][0]) / 2
					y2 = points[i + 1 - n][1] if oncurve[i + 1 - n] else (points[i][1] + points[i + 1 - n][1]) / 2
					xx = bezier2(x1, points[i][0], x2, t)
					yy = bezier2(y1, points[i][1], y2, t)
					px.extend(xx)
					py.extend(yy)
			px = pos_x + array(px) * xscale
			py = pos_y + array(py) * yscale
			shapes += make_polygon(layer, px, py, hole=(polygon_direction(px, py) == "ccw"), order=order)
		
		# move position again
		pos_x += face.glyph.advance.x * xscale
	
	return shapes

def pcb_transform(shapes, xfrom, yfrom, xto, yto, angle, flip):
	angle_sin = sin(angle * pi / 180)
	angle_cos = cos(angle * pi / 180)
	m11 = -angle_cos if flip else angle_cos
	m12 = -angle_sin
	m21 = -angle_sin if flip else angle_sin
	m22 = angle_cos
	#m11 = angle_cos
	#m12 = -angle_sin
	#m21 = angle_sin
	#m22 = angle_cos
	offset_x = xto - xfrom * m11 - yfrom * m12
	offset_y = yto - xfrom * m21 - yfrom * m22
	def transform(x, y):
		return (
			offset_x + x * m11 + y * m12,
			offset_y + x * m21 + y * m22,
		)
	for shape in shapes:
		if flip:
			if shape["layer"].endswith("-top"):
				shape["layer"] = shape["layer"][:-4] + "-bot"
			elif shape["layer"].endswith("-bot"):
				shape["layer"] = shape["layer"][:-4] + "-top"
		(shape["x"], shape["y"]) = transform(shape["x"], shape["y"])
		if shape["type"] == "rectangle":
			shape["angle"] += angle

def pcb_plot(name, shapes, layers=None):
	figure(name, figsize=(12, 10))
	patches = []
	unknown_layers = set()
	for shape in shapes:
		layerdef = layerstack.get(shape["layer"])
		if layerdef is None:
			unknown_layers.add(shape["layer"])
		else:
			if layers is not None and shape["layer"] not in layers:
				continue
			edgecolor=(layerdef["color"][0]*0.5, layerdef["color"][1]*0.5, layerdef["color"][2]*0.5, 0.5)
			facecolor=(layerdef["color"][0], layerdef["color"][1], layerdef["color"][2], 0.3)
			poly = shape_to_polygon(shape)
			if shape["outline"] is None:
				patches.append(matplotlib.patches.Polygon(poly, edgecolor=edgecolor, facecolor=facecolor, fill=not shape["hole"]))
			else:
				first = 1 if shape["type"] == "polygon" and not shape["closed"] else 0
				for i in range(first, len(poly)):
					poly2 = stroke_line(poly[i - 1, 0], poly[i - 1, 1], poly[i, 0], poly[i, 1], shape["outline"], True, True)
					patches.append(matplotlib.patches.Polygon(poly2, edgecolor=edgecolor, facecolor=facecolor, fill=not shape["hole"]))
	if len(unknown_layers) != 0:
		print("Unknown layers: " + ", ".join(unknown_layers))
	ax = subplot(1, 1, 1)
	if len(patches) != 0:
		ax.add_collection(matplotlib.collections.PatchCollection(patches, match_original=True))
	grid()
	axis("equal")
	tight_layout()
	show()

def pcb_export(shapes, path, name, use_arcs=False):
	
	# delete old files
	if os.path.isdir(path + "/" + name):
		fnames = os.listdir(path + "/" + name)
		for fname in fnames:
			ok = False
			for layer in layerstack:
				ls = layerstack[layer]
				if ls["type"] is not None:
					if fname == name + ls["ext"]:
						ok = True
			if not ok:
				raise Exception("Output directory contains unknown file '%s' which would be deleted by export." % (fname))
		for fname in fnames:
			os.remove(path + "/" + name + "/" + fname)
	else:
		os.mkdir(path + "/" + name)
	
	# write new files
	unknown_layers = set()
	for shape in shapes:
		layerdef = layerstack.get(shape["layer"])
		if layerdef is None:
			unknown_layers.add(shape["layer"])
	if len(unknown_layers) != 0:
		print("Unknown layers: " + ", ".join(unknown_layers))
	for layer in layerstack:
		ls = layerstack[layer]
		if ls["type"] is not None:
			filename = path + "/" + name + "/" + name + ls["ext"]
			if ls["type"] == "gerber":
				pcb_export_gerber(shapes, layer, filename, use_arcs)
			elif ls["type"] == "drill":
				pcb_export_drill(shapes, layer, filename)
			else:
				raise Exception("Unknown layer type!")
	
	# create zip file
	if os.path.isfile(path + "/" + name + ".zip"):
		os.remove(path + "/" + name + ".zip")
	subprocess.call(["zip", "-r", name + ".zip", name], cwd=path)

def pcb_export_gerber(shapes, layer, filename, use_arcs):
	global toolcounter	
	scale = 10**4 # 4.4 format, mm
	tools = []
	tools_circle = {}
	tools_rectangle = {}
	shapes_order = {}
	toolcounter = 10 # first D-code for tools is D10
	needs_rr = False
	
	def ff(num):
		if num < 0:
			return "-%08d" % (-num)
		else:
			return "%08d" % (num)
	
	def add_circle(diam):
		global toolcounter
		diam = int(round(diam * scale))
		if diam not in tools_circle:
			tools.append((toolcounter, "circle", diam))
			tools_circle[diam] = toolcounter
			toolcounter += 1
	def add_rectangle(width, height, angle):
		global toolcounter, needs_rr
		width = int(round(width * scale))
		height = int(round(height * scale))
		angle = int(round(angle * scale)) % 1800000
		if angle >= 900000:
			(width, height) = (height, width)
			angle -= 900000
		if angle != 0:
			needs_rr = True
		if (width, height, angle) not in tools_rectangle:
			tools.append((toolcounter, "rectangle", width, height, angle))
			tools_rectangle[(width, height, angle)] = toolcounter
			toolcounter += 1
	def find_circle(diam):
		diam = int(round(diam * scale))
		return tools_circle[diam]
	def find_rectangle(width, height, angle):
		width = int(round(width * scale))
		height = int(round(height * scale))
		angle = int(round(angle * scale)) % 1800000
		if angle >= 900000:
			(width, height) = (height, width)
			angle -= 900000
		return tools_rectangle[(width, height, angle)]
	
	def flatten_circle(x, y, radius):
		angle = linspace(0, 2 * pi, circle_steps(radius), endpoint=False)
		rx = x + radius * cos(angle)
		ry = y + radius * sin(angle)
		return (rx, ry)
	def flatten_rectangle(x, y, width, height, angle):
		rx = array([-width  / 2,  width  / 2,  width  / 2, -width  / 2])
		ry = array([-height / 2, -height / 2,  height / 2,  height / 2])
		rrx = x + rx * cos(angle * pi / 180) - ry * sin(angle * pi / 180)
		rry = y + rx * sin(angle * pi / 180) + ry * cos(angle * pi / 180)
		return (rrx, rry)
	
	def write_flash(num, x, y):
		f.write("D%02d*\n" % (num))
		f.write("X%sY%sD03*\n" % (ff(int(round(x * scale))), ff(int(round(y * scale)))))
	def write_region(rx, ry):
		px = numpy.round(rx * scale).astype(int32)
		py = numpy.round(ry * scale).astype(int32)
		f.write("G36*\n")
		f.write("G01*\n")
		f.write("X%sY%sD02*\n" % (ff(px[0]), ff(py[0])))
		for j in range(1, len(px)):
			f.write("X%sY%sD01*\n" % (ff(px[j]), ff(py[j])))
		f.write("X%sY%sD01*\n" % (ff(px[0]), ff(py[0])))
		f.write("D02*\n")
		f.write("G37*\n")
	def write_region_circle(x, y, radius):
		x1 = int(round((x - radius) * scale))
		x2 = int(round(x * scale))
		y1 = int(round(y * scale))
		y2 = int(round(y * scale))
		f.write("G36*\n")
		f.write("G02*\n")
		f.write("G75*\n")
		f.write("X%sY%sD02*\n" % (ff(x1), ff(y1)))
		f.write("X%sY%sI%sJ%sD01*\n" % (ff(x1), ff(y1), ff(x2 - x1), ff(y2 - y1)))
		f.write("D02*\n")
		f.write("G37*\n")
	def write_outline(num, rx, ry, closed):
		px = numpy.round(rx * scale).astype(int32)
		py = numpy.round(ry * scale).astype(int32)
		f.write("D%02d*\n" % (num))
		f.write("G01*\n")
		f.write("X%sY%sD02*\n" % (ff(px[0]), ff(py[0])))
		for j in range(1, len(px)):
			f.write("X%sY%sD01*\n" % (ff(px[j]), ff(py[j])))
		if closed:
			f.write("X%sY%sD01*\n" % (ff(px[0]), ff(py[0])))
	def write_outline_circle(num, x, y, radius):
		x1 = int(round((x - radius) * scale))
		x2 = int(round(x * scale))
		y1 = int(round(y * scale))
		y2 = int(round(y * scale))
		f.write("D%02d*\n" % (num))
		f.write("G02*\n")
		f.write("G75*\n")
		f.write("X%sY%sD02*\n" % (ff(x1), ff(y1)))
		f.write("X%sY%sI%sJ%sD01*\n" % (ff(x1), ff(y1), ff(x2 - x1), ff(y2 - y1)))
	
	# collect tools
	for shape in shapes:
		if shape["layer"] != layer:
			continue
		if shape["outline"] is None:
			if shape["type"] == "circle":
				if shape["pad"]:
					add_circle(shape["radius"] * 2)
			elif shape["type"] == "rectangle":
				if shape["pad"]:
					add_rectangle(shape["width"], shape["height"], shape["angle"])
			elif shape["type"] == "polygon":
				pass
			else:
				raise Exception("Unknown shape type!")
		else:
			add_circle(shape["outline"])
		order = shape["order"] * 2 + 1 if shape["hole"] else shape["order"] * 2
		if order not in shapes_order:
			shapes_order[order] = []
		shapes_order[order].append(shape)
	
	# write file
	with open(filename, "w") as f:
		f.write("%FSLAX44Y44*%\n")
		f.write("%MOMM*%\n")
		if needs_rr:
			f.write("%AMRR*21,1,$1,$2,0,0,$3*%\n")
		for tool in tools:
			if tool[1] == "circle":
				f.write("%%ADD%02dC,%.4f*%%\n" % (tool[0], tool[2] / scale))
			elif tool[1] == "rectangle":
				if tool[4] == 0:
					f.write("%%ADD%02dR,%.4fX%.4f*%%\n" % (tool[0], tool[2] / scale, tool[3] / scale))
				else:
					f.write("%%ADD%02dRR,%.4fX%.4fX%.4f*%%\n" % (tool[0], tool[2] / scale, tool[3] / scale, tool[4] / scale))
		orders = list(shapes_order.keys())
		orders.sort()
		for order in orders:
			if order % 2 == 0:
				f.write("%LPD*%\n")
			else:
				f.write("%LPC*%\n")
			for shape in shapes_order[order]:
				if shape["outline"] is None:
					if shape["type"] == "circle":
						if shape["pad"]:
							num = find_circle(shape["radius"] * 2)
							write_flash(num, shape["x"], shape["y"])
						elif use_arcs:
							write_region_circle(shape["x"], shape["y"], shape["radius"])
						else:
							(rx, ry) = flatten_circle(shape["x"], shape["y"], shape["radius"])
							write_region(rx, ry)
					elif shape["type"] == "rectangle":
						if shape["pad"]:
							num = find_rectangle(shape["width"], shape["height"], shape["angle"])
							write_flash(num, shape["x"], shape["y"])
						else:
							(rx, ry) = flatten_rectangle(shape["x"], shape["y"], shape["width"], shape["height"], shape["angle"])
							write_region(rx, ry)
					elif shape["type"] == "polygon":
						write_region(shape["x"], shape["y"])
					else:
						raise Exception("Unknown shape type!")
				else:
					num = find_circle(shape["outline"])
					if shape["type"] == "circle":
						if use_arcs:
							write_outline_circle(num, shape["x"], shape["y"], shape["radius"])
						else:
							(rx, ry) = flatten_circle(shape["x"], shape["y"], shape["radius"])
							write_outline(num, rx, ry, True)
					elif shape["type"] == "rectangle":
						(rx, ry) = flatten_rectangle(shape["x"], shape["y"], shape["width"], shape["height"], shape["angle"])
						write_outline(num, rx, ry, True)
					elif shape["type"] == "polygon":
						write_outline(num, shape["x"], shape["y"], shape["closed"])
					else:
						raise Exception("Unknown shape type!")
		f.write("M02*\n")

def pcb_export_drill(shapes, layer, filename):
	
	scale = 10**4 # 4.4 format, mm
	
	def ff(num):
		if num < 0:
			return "-%08d" % (-num)
		else:
			return "%08d" % (num)
	
	# collect tools
	tools = {}
	for shape in shapes:
		if shape["layer"] != layer:
			continue
		if shape["type"] != "circle":
			raise Exception("Drill file only supports circular holes!")
		diam = shape["radius"] * 2
		if diam not in tools:
			tools[diam] = []
		tools[diam].append((shape["x"], shape["y"]))
	
	# write file
	with open(filename, "w") as f:
		f.write("M48\n")
		f.write("METRIC\n")
		num = 0
		for diam in tools:
			num += 1
			f.write("T%02dC%.4f\n" % (num, diam))
		f.write("%\n")
		num = 0
		for diam in tools:
			num += 1
			holes = tools[diam]
			f.write("T%02d\n" % (num))
			for hole in holes:
				f.write("X%sY%s\n" % (ff(int(round(hole[0] * scale))), ff(int(round(hole[1] * scale)))))
		f.write("M30\n")

registry = {}
def register(func):
	registry[func.__name__] = func
	return func
def place(name, x, y, angle, flip, **kwargs):
	func = registry.get(name)
	if func is None:
		raise Exception("Unknown component '%s'!" % (name))
	shapes = func(**kwargs)
	pcb_transform(shapes, 0.0, 0.0, x, y, angle, flip)
	return shapes
