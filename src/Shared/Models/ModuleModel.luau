--!nonstrict
--[[
	ModuleModel: geometria procedurale dei moduli di difesa.
	Build(moduleId, altId, mode) -> Model con PrimaryPart "Root" centrato sulla cella principale.
	mode: "home" | "raid" | "visit" | "ghost". Gli attributi sul Root descrivono il comportamento
	(letti dal client per animazione/push e dal server per la simulazione del raid).
]]
local Defenses = require(script.Parent.Parent.Catalog.Defenses)
local Config = require(script.Parent.Parent.Config)
local PartUtil = require(script.Parent.PartUtil)
local MeshUtil = require(script.Parent.MeshUtil)

local CELL = Config.Grid.CellSize
local ModuleModel = {}

local function root(model, moduleId, params, cellCount)
	local r = PartUtil.Part({ Size = Vector3.new(CELL, 0.2, CELL), Transparency = 1, CanCollide = false, CanQuery = false, CFrame = CFrame.new(), Parent = model, Name = "Root" })
	model.PrimaryPart = r
	r:SetAttribute("ModuleId", moduleId)
	for k, v in pairs(params) do
		if type(v) == "number" or type(v) == "boolean" or type(v) == "string" then
			r:SetAttribute(k, v)
		end
	end
	return r
end

local builders = {}

builders.corrente = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	-- bocchette alle 3 celle (asse X locale)
	for dx = -1, 1 do
		local base = MeshUtil.Make("vent", 2.8, { Color = Color3.fromRGB(120, 190, 170), Material = Enum.Material.Metal, CFrame = CFrame.new(dx * CELL, 0.36, 0), Parent = model, Name = "Vent", CanCollide = true })
			or PartUtil.Cylinder(1.3, 0.5, Color3.fromRGB(120, 190, 170), CFrame.new(dx * CELL, 0.25, 0), model, { Material = Enum.Material.Metal, Name = "Vent" })
		PartUtil.Cylinder(0.8, 0.3, def.Color, CFrame.new(dx * CELL, 0.55, 0), model, { Material = Enum.Material.Neon, Name = "VentGlow", CanCollide = false })
		PartUtil.Light(base, def.Color, 0.6, 7)
	end
	-- zona di spinta (invisibile; il client applica la spinta leggendo Dir/Push)
	local zone = PartUtil.Part({ Size = Vector3.new(CELL * 3, 9, CELL), Transparency = params.Up and 0.9 or 0.92, Color = def.Color, Material = Enum.Material.ForceField, CanCollide = false, CanQuery = false, CFrame = CFrame.new(0, 4.5, 0), Parent = model, Name = "Zone" })
	zone:SetAttribute("Push", params.Push or 55)
	zone:SetAttribute("Up", params.Up == true)
	zone:SetAttribute("Pulse", params.Pulse == true)
	zone:SetAttribute("PulsePeriod", params.PulsePeriod or 2.4)
	zone:SetAttribute("Active", true)
	zone:SetAttribute("Dir", 1) -- +1 / -1 lungo l'asse X locale (la campana lo inverte)
	-- particelle telegrafate: foglie/strisce di vento nella direzione di spinta
	local e = PartUtil.Emitter(zone, {
		Color = Color3.fromRGB(220, 255, 240), Rate = 18, Speed = NumberRange.new(12, 18), Lifetime = NumberRange.new(0.5, 0.8),
		Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.15), NumberSequenceKeypoint.new(0.3, 0.5), NumberSequenceKeypoint.new(1, 0) }),
		Spread = Vector2.new(10, 10), Acceleration = Vector3.new(0, 0, 0), LightEmission = 0.4, Name = "Wind",
	})
	e.EmissionDirection = Enum.NormalId.Right
	e.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.5), NumberSequenceKeypoint.new(1, 1) })
	return r
end

builders.piattaforma = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	-- bordi del vuoto
	for _, dz in ipairs({ -1.5, 1.5 }) do
		PartUtil.Part({ Size = Vector3.new(CELL, 0.5, 0.4), Color = Color3.fromRGB(255, 230, 170), Material = Enum.Material.Neon, CFrame = CFrame.new(0, 0.1, dz * CELL), Parent = model, Name = "Edge", CanCollide = false })
	end
	-- fondo del vuoto: cielo scuro (visual) — in raid non è calpestabile
	PartUtil.Part({ Size = Vector3.new(CELL, 0.2, CELL * 3), Color = Color3.fromRGB(80, 110, 170), Material = Enum.Material.Glass, Transparency = 0.35, CFrame = CFrame.new(0, -1.2, 0), Parent = model, Name = "Void", CanCollide = false, CanQuery = false })
	local width = (params.Width or 1) * 3.4
	local plat = MeshUtil.Make("platform_pad", Vector3.new(width, 0.7, width), { Color = def.Color, Material = Enum.Material.SmoothPlastic, CFrame = CFrame.new(0, 0.1, -CELL), Parent = model, Name = "Platform", CanCollide = true })
		or PartUtil.Part({ Size = Vector3.new(width, 0.7, width), Color = def.Color, Material = Enum.Material.SmoothPlastic, CFrame = CFrame.new(0, 0.1, -CELL), Parent = model, Name = "Platform" })
	plat:SetAttribute("Period", params.Period or 3.2)
	plat:SetAttribute("Travel", CELL * 2) -- da -CELL a +CELL lungo Z locale
	plat:SetAttribute("Phase", 0)
	PartUtil.Light(plat, def.Color, 0.8, 8)
	if params.Double then
		local plat2 = plat:Clone()
		plat2.Name = "Platform2"
		plat2:SetAttribute("Phase", 0.5)
		plat2.Parent = model
	end
	return r
end

builders.sentinella = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	local pillar = MeshUtil.Make("pillar", { Height = 7 }, { Color = Color3.fromRGB(205, 210, 230), Material = Enum.Material.Slate, CFrame = CFrame.new(0, 3.5, 0), Parent = model, Name = "Pillar", CanCollide = true })
	if not pillar then
		pillar = PartUtil.Cylinder(1.1, 7, Color3.fromRGB(205, 210, 230), CFrame.new(0, 3.5, 0), model, { Material = Enum.Material.Slate, Name = "Pillar" })
		PartUtil.Cylinder(1.5, 0.6, Color3.fromRGB(180, 190, 215), CFrame.new(0, 0.3, 0), model, { Material = Enum.Material.Slate, Name = "Base" })
	end
	local lamp = MeshUtil.Make("lamp_head", 2.4, { Color = Color3.fromRGB(255, 250, 200), Material = Enum.Material.Neon, CFrame = CFrame.new(0, 7.8, 0), Parent = model, Name = "Lamp" })
		or PartUtil.Ball(2.2, Color3.fromRGB(255, 250, 200), CFrame.new(0, 7.6, 0), model, { Material = Enum.Material.Neon, Name = "Lamp", CanCollide = false })
	PartUtil.Light(lamp, Color3.fromRGB(255, 240, 180), 1.5, 16)
	-- cono di luce: ventaglio di fasci Neon a terra (apice al pilastro). Orientato da ModuleModel.OrientSentinel
	local radius = params.Radius or 9
	local arc = params.Arc or 50
	local cone = PartUtil.Part({ Size = Vector3.new(0.2, 0.2, 0.2), Transparency = 1, CanCollide = false, CanQuery = false, CFrame = CFrame.new(0, 0.3, 0), Parent = model, Name = "Cone", CastShadow = false })
	cone:SetAttribute("Radius", radius)
	cone:SetAttribute("Arc", arc)
	cone:SetAttribute("Speed", params.Speed or 55)
	cone:SetAttribute("Erratic", params.Erratic == true)
	local beams = 5
	for i = 1, beams do
		local frac = (i - 1) / (beams - 1) - 0.5
		local beam = PartUtil.Part({ Size = Vector3.new(0.7, 0.18, radius), Color = Color3.fromRGB(255, 245, 170), Material = Enum.Material.Neon, Transparency = 0.35 + math.abs(frac) * 0.4, CanCollide = false, CanQuery = false, Parent = model, Name = "Beam", CastShadow = false })
		beam:SetAttribute("BeamAngle", frac * arc)
	end
	-- disco di luce al suolo intorno al pilastro
	PartUtil.Cylinder(2.2, 0.1, Color3.fromRGB(255, 245, 170), CFrame.new(0, 0.12, 0), model, { Material = Enum.Material.Neon, Transparency = 0.5, Name = "Glow", CanCollide = false, CanQuery = false })
	r:SetAttribute("Angle", 0)
	ModuleModel.OrientSentinel(model, 0)
	return r
end

builders.muro_nube = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	local cells = (params.Long and { -1, 0, 1 }) or { 0, 1 }
	for _, dx in ipairs(cells) do
		local block = PartUtil.Part({ Size = Vector3.new(CELL, 6, CELL), Color = Color3.fromRGB(240, 244, 255), Material = Enum.Material.SmoothPlastic, CFrame = CFrame.new(dx * CELL, 3, 0), Parent = model, Name = "Wall" })
		PartUtil.Cloud(CFrame.new(dx * CELL, 6.2, 0), 1.3, model, Color3.fromRGB(250, 252, 255), 0)
		PartUtil.Cloud(CFrame.new(dx * CELL, 1.2, 0), 1.0, model, Color3.fromRGB(244, 247, 255), 0)
		block.CanCollide = true
	end
	return r
end

builders.faro = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	local _ = MeshUtil.Make("basin", Vector3.new(3.6, 1.0, 3.6), { Color = Color3.fromRGB(230, 225, 210), Material = Enum.Material.Marble, CFrame = CFrame.new(0, 0.5, 0), Parent = model, Name = "Basin", CanCollide = true })
		or PartUtil.Cylinder(1.7, 0.8, Color3.fromRGB(230, 225, 210), CFrame.new(0, 0.4, 0), model, { Material = Enum.Material.Marble, Name = "Basin" })
	local glow = PartUtil.Cylinder(1.25, 0.3, Color3.fromRGB(255, 205, 90), CFrame.new(0, 0.85, 0), model, { Material = Enum.Material.Neon, Name = "FakePool", CanCollide = false })
	PartUtil.Light(glow, Color3.fromRGB(255, 200, 90), 1.4, 12)
	PartUtil.Emitter(glow, { Color = Color3.fromRGB(255, 220, 120), Rate = 10, Speed = NumberRange.new(1, 3), Lifetime = NumberRange.new(0.6, 1.2), Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.3), NumberSequenceKeypoint.new(1, 0) }), Name = "Lure" })
	r:SetAttribute("Dazzle", params.Dazzle or 3.5)
	r:SetAttribute("TriggerRadius", 3.2)
	return r
end

builders.nebbia = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	local zone = PartUtil.Part({ Size = Vector3.new(CELL * 2, 7, CELL * 2), Transparency = 1, CanCollide = false, CanQuery = false, CFrame = CFrame.new(CELL / 2, 3.5, CELL / 2), Parent = model, Name = "FogZone" })
	for i = 1, 3 do
		local a = i * 2.1
		PartUtil.Cloud(CFrame.new(CELL / 2 + math.cos(a) * 1.8, 1.4 + (i % 2) * 0.9, CELL / 2 + math.sin(a) * 1.8), 1.3, model, Color3.fromRGB(225, 232, 245), 0.5)
	end
	PartUtil.Emitter(zone, { Color = Color3.fromRGB(230, 236, 248), Rate = 10, Speed = NumberRange.new(0.3, 0.8), Lifetime = NumberRange.new(2, 3.5), Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 2), NumberSequenceKeypoint.new(0.5, 4), NumberSequenceKeypoint.new(1, 2) }), Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.7), NumberSequenceKeypoint.new(0.5, 0.45), NumberSequenceKeypoint.new(1, 1) }), LightEmission = 0.1, Name = "Fog" })
	return r
end

builders.scivolo = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	for dx = 0, 1 do
		local wet = PartUtil.Part({ Size = Vector3.new(CELL, 0.15, CELL), Color = Color3.fromRGB(150, 225, 180), Material = Enum.Material.Glass, Transparency = 0.25, Reflectance = 0.2, CFrame = CFrame.new(dx * CELL, 0.08, 0), Parent = model, Name = "WetTile" })
		wet.CustomPhysicalProperties = PhysicalProperties.new(0.7, params.Friction or 0.05, 0.2, 100, 1)
		PartUtil.Emitter(wet, { Color = Color3.fromRGB(200, 240, 255), Rate = 4, Speed = NumberRange.new(0.5, 1.5), Lifetime = NumberRange.new(0.5, 1), Size = NumberSequence.new(0.12), Name = "Dew" })
	end
	return r
end

builders.cupola = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	-- cristallo di controllo decorativo sulla cella del modulo
	local crystal = MeshUtil.Make("crystal", { Height = 3.4 }, { Color = def.Color, Material = Enum.Material.Glass, Transparency = 0.2, Reflectance = 0.3, CFrame = CFrame.new(0, 2.0, 0), Parent = model, Name = "Crystal" })
		or PartUtil.Part({ Size = Vector3.new(1.4, 3.2, 1.4), Color = def.Color, Material = Enum.Material.Glass, Transparency = 0.2, Reflectance = 0.3, CFrame = CFrame.new(0, 1.8, 0) * CFrame.Angles(0, math.rad(45), 0), Parent = model, Name = "Crystal", CanCollide = false })
	PartUtil.Light(crystal, def.Color, 1.2, 12)
	PartUtil.Cylinder(1.2, 0.5, Color3.fromRGB(200, 190, 230), CFrame.new(0, 0.25, 0), model, { Material = Enum.Material.Marble, Name = "Base" })
	r:SetAttribute("Height", params.Height or 7)
	return r
end

builders.campana = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	for _, dx in ipairs({ -1.4, 1.4 }) do
		local _ = MeshUtil.Make("post", { Height = 6 }, { Color = Color3.fromRGB(120, 90, 60), Material = Enum.Material.Wood, CFrame = CFrame.new(dx, 3, 0), Parent = model, Name = "Post", CanCollide = true })
			or PartUtil.Part({ Size = Vector3.new(0.4, 6, 0.4), Color = Color3.fromRGB(120, 90, 60), Material = Enum.Material.Wood, CFrame = CFrame.new(dx, 3, 0), Parent = model, Name = "Post" })
	end
	PartUtil.Part({ Size = Vector3.new(3.4, 0.4, 0.5), Color = Color3.fromRGB(120, 90, 60), Material = Enum.Material.Wood, CFrame = CFrame.new(0, 6.1, 0), Parent = model, Name = "Beam" })
	local bell = MeshUtil.Make("bell", { Height = 2.2 }, { Color = Color3.fromRGB(240, 200, 110), Material = Enum.Material.Metal, Reflectance = 0.35, CFrame = CFrame.new(0, 4.9, 0), Parent = model, Name = "Bell" })
	if not bell then
		bell = PartUtil.Cylinder(1.1, 1.8, Color3.fromRGB(240, 200, 110), CFrame.new(0, 4.6, 0), model, { Material = Enum.Material.Metal, Reflectance = 0.35, Name = "Bell", CanCollide = false })
		PartUtil.Ball(0.9, Color3.fromRGB(240, 200, 110), CFrame.new(0, 5.6, 0), model, { Material = Enum.Material.Metal, Reflectance = 0.35, Name = "BellTop" })
	end
	PartUtil.Light(bell, Color3.fromRGB(255, 220, 140), 0.8, 10)
	r:SetAttribute("TriggerFraction", params.TriggerFraction or 0.5)
	return r
end

builders.arcobaleno = function(model, def, params, mode)
	local r = root(model, def.Id, params)
	-- vuoto di 3 celle lungo Z
	PartUtil.Part({ Size = Vector3.new(CELL, 0.2, CELL * 3), Color = Color3.fromRGB(80, 110, 170), Material = Enum.Material.Glass, Transparency = 0.35, CFrame = CFrame.new(0, -1.2, CELL), Parent = model, Name = "Void", CanCollide = false, CanQuery = false })
	local colors = { Color3.fromRGB(255, 120, 120), Color3.fromRGB(255, 200, 100), Color3.fromRGB(150, 230, 140), Color3.fromRGB(120, 180, 255), Color3.fromRGB(200, 140, 255) }
	local bridge = PartUtil.Part({ Size = Vector3.new(CELL * 0.9, 0.5, CELL * 3), Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.Neon, Transparency = 0.1, CFrame = CFrame.new(0, 0.1, CELL), Parent = model, Name = "Bridge" })
	for i, c in ipairs(colors) do
		local stripe = PartUtil.Part({ Size = Vector3.new(CELL * 0.9 / #colors, 0.52, CELL * 3), Color = c, Material = Enum.Material.Neon, Transparency = 0.15, CFrame = CFrame.new(-CELL * 0.45 + (i - 0.5) * (CELL * 0.9 / #colors), 0.1, CELL), Parent = model, Name = "Stripe", CanCollide = false, CanQuery = false })
		stripe:SetAttribute("BridgeVisual", true)
	end
	bridge:SetAttribute("Period", params.Period or 4)
	bridge:SetAttribute("Visible", true)
	return r
end

-- Orienta i fasci della sentinella (angolo in gradi, 0 = -Z locale del Root). Usato da server (raid) e client (cosmetico).
function ModuleModel.OrientSentinel(model, angleDeg)
	local root = model.PrimaryPart or model:FindFirstChild("Root")
	if not root then
		return
	end
	local radius = (model:FindFirstChild("Cone") and model.Cone:GetAttribute("Radius")) or 9
	local base = CFrame.new(root.Position) * CFrame.Angles(0, -math.rad(angleDeg), 0)
	for _, beam in ipairs(model:GetChildren()) do
		if beam.Name == "Beam" then
			local a = beam:GetAttribute("BeamAngle") or 0
			beam.CFrame = base * CFrame.Angles(0, -math.rad(a), 0) * CFrame.new(0, 0.3, -radius / 2)
		end
	end
	root:SetAttribute("Angle", angleDeg)
	return base
end

-- Costruisce il modello; la CFrame viene impostata dal chiamante tramite PivotTo
function ModuleModel.Build(moduleId, altId, mode, parent)
	local def = Defenses.Get(moduleId)
	if not def then
		return nil
	end
	local params = Defenses.EffectiveParams(moduleId, altId)
	local model = PartUtil.Model("Module_" .. moduleId, nil)
	model:SetAttribute("ModuleId", moduleId)
	model:SetAttribute("Alt", altId or "base")
	model:SetAttribute("Category", def.Category)
	local builder = builders[moduleId]
	if builder then
		builder(model, def, params, mode or "home")
	else
		root(model, moduleId, params)
	end
	if mode == "ghost" then
		for _, d in ipairs(model:GetDescendants()) do
			if d:IsA("BasePart") then
				d.CanCollide = false
				d.CanQuery = false
				d.Transparency = math.max(d.Transparency, 0.5)
			elseif d:IsA("ParticleEmitter") or d:IsA("PointLight") then
				d.Enabled = false
			elseif d:IsA("ProximityPrompt") then
				d:Destroy()
			end
		end
	end
	if parent then
		model.Parent = parent
	end
	return model
end

return ModuleModel
