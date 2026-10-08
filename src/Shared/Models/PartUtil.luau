--!nonstrict
-- Helper per costruire geometria procedurale in modo conciso.
local PartUtil = {}
local MeshUtil = require(script.Parent.MeshUtil)
local CLOUD_VARIANTS = { "cloud_a", "cloud_b", "cloud_c" }

function PartUtil.Part(props)
	local p = Instance.new(props.Class or "Part")
	p.Anchored = true
	p.CanCollide = props.CanCollide ~= false
	p.CanTouch = props.CanTouch == true
	p.CanQuery = props.CanQuery ~= false
	p.CastShadow = props.CastShadow ~= false
	p.Material = props.Material or Enum.Material.SmoothPlastic
	p.Color = props.Color or Color3.fromRGB(255, 255, 255)
	p.Transparency = props.Transparency or 0
	p.Reflectance = props.Reflectance or 0
	p.Size = props.Size or Vector3.new(1, 1, 1)
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	if props.Shape and p:IsA("Part") then
		p.Shape = props.Shape
	end
	if props.CFrame then
		p.CFrame = props.CFrame
	elseif props.Position then
		p.Position = props.Position
	end
	p.Name = props.Name or "Part"
	if props.Attributes then
		for k, v in pairs(props.Attributes) do
			p:SetAttribute(k, v)
		end
	end
	if props.Parent then
		p.Parent = props.Parent
	end
	return p
end

function PartUtil.Ball(size, color, cf, parent, extra)
	local props = { Shape = Enum.PartType.Ball, Size = Vector3.new(size, size, size), Color = color, CFrame = cf, Parent = parent, CanCollide = false }
	if extra then
		for k, v in pairs(extra) do
			props[k] = v
		end
	end
	return PartUtil.Part(props)
end

function PartUtil.Cylinder(radius, height, color, cf, parent, extra)
	-- il cilindro Roblox è orientato lungo X: ruotiamo per averlo verticale
	local props = { Shape = Enum.PartType.Cylinder, Size = Vector3.new(height, radius * 2, radius * 2), Color = color, CFrame = cf * CFrame.Angles(0, 0, math.rad(90)), Parent = parent }
	if extra then
		for k, v in pairs(extra) do
			props[k] = v
		end
	end
	return PartUtil.Part(props)
end

function PartUtil.Light(parent, color, brightness, range)
	local l = Instance.new("PointLight")
	l.Color = color
	l.Brightness = brightness or 1
	l.Range = range or 12
	l.Shadows = false
	l.Parent = parent
	return l
end

function PartUtil.Emitter(parent, props)
	local e = Instance.new("ParticleEmitter")
	e.Color = ColorSequence.new(props.Color or Color3.new(1, 1, 1))
	e.Size = props.Size or NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.3), NumberSequenceKeypoint.new(1, 0) })
	e.Transparency = props.Transparency or NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.2), NumberSequenceKeypoint.new(1, 1) })
	e.Lifetime = props.Lifetime or NumberRange.new(0.8, 1.6)
	e.Rate = props.Rate or 4
	e.Speed = props.Speed or NumberRange.new(0.5, 1.5)
	e.SpreadAngle = props.Spread or Vector2.new(180, 180)
	e.Acceleration = props.Acceleration or Vector3.new(0, 0.5, 0)
	e.LightEmission = props.LightEmission or 0.6
	e.LightInfluence = 0.2
	e.Rotation = NumberRange.new(0, 360)
	e.RotSpeed = NumberRange.new(-40, 40)
	e.Drag = props.Drag or 1
	e.Enabled = props.Enabled ~= false
	e.Name = props.Name or "Emitter"
	if props.Texture then
		e.Texture = props.Texture
	end
	e.Parent = parent
	return e
end

function PartUtil.Billboard(parent, props)
	local bb = Instance.new("BillboardGui")
	bb.Name = props.Name or "Billboard"
	bb.Size = props.Size or UDim2.fromOffset(160, 44)
	bb.StudsOffset = props.Offset or Vector3.new(0, 3, 0)
	bb.AlwaysOnTop = props.AlwaysOnTop == true
	bb.MaxDistance = props.MaxDistance or 90
	bb.LightInfluence = 0
	bb.Parent = parent
	local label = Instance.new("TextLabel")
	label.Name = "Label"
	label.BackgroundTransparency = 1
	label.Size = UDim2.fromScale(1, 1)
	label.Font = Enum.Font.FredokaOne
	label.TextScaled = true
	label.TextColor3 = props.TextColor or Color3.new(1, 1, 1)
	label.TextStrokeTransparency = 0.4
	label.TextStrokeColor3 = Color3.fromRGB(30, 40, 70)
	label.Text = props.Text or ""
	label.Parent = bb
	return bb, label
end

function PartUtil.Prompt(parent, actionText, objectText, holdDuration, maxDistance)
	local pp = Instance.new("ProximityPrompt")
	pp.ActionText = actionText
	pp.ObjectText = objectText or ""
	pp.HoldDuration = holdDuration or 0
	pp.MaxActivationDistance = maxDistance or 10
	pp.RequiresLineOfSight = false
	pp.Style = Enum.ProximityPromptStyle.Default
	pp.Parent = parent
	return pp
end

function PartUtil.Model(name, parent)
	local m = Instance.new("Model")
	m.Name = name
	if parent then
		m.Parent = parent
	end
	return m
end

-- Nuvola soffice: gruppo di sfere bianche
function PartUtil.Cloud(cf, scale, parent, color, transparency)
	local m = PartUtil.Model("Cloud", parent)
	color = color or Color3.fromRGB(250, 252, 255)
	-- mesh di cumulo (variante scelta in modo deterministico dalla posizione)
	local variant = CLOUD_VARIANTS[(math.floor(math.abs(cf.X * 7 + cf.Z * 13 + cf.Y * 3)) % 3) + 1]
	local mesh = MeshUtil.Make(variant, scale * 3.6, { Color = color, Transparency = transparency or 0, CFrame = cf * CFrame.Angles(0, (cf.X + cf.Z) * 0.37, 0), Parent = m, CastShadow = false, Name = "CloudMesh" })
	if mesh then
		return m
	end
	local offsets = {
		{ 0, 0, 0, 1 }, { 0.9, -0.1, 0.2, 0.75 }, { -0.9, -0.05, -0.1, 0.8 }, { 0.3, 0.35, -0.4, 0.6 }, { -0.4, 0.3, 0.5, 0.55 }, { 0.1, -0.3, 0.8, 0.6 },
	}
	for _, o in ipairs(offsets) do
		PartUtil.Ball(scale * o[4] * 2, color, cf * CFrame.new(o[1] * scale, o[2] * scale, o[3] * scale), m, { Transparency = transparency or 0.05, CastShadow = false, Material = Enum.Material.SmoothPlastic })
	end
	return m
end

return PartUtil
