--!nonstrict
--[[
	CreatureModel: costruisce un Nimbino proceduralmente (nessun asset esterno).
	Il PrimaryPart è il corpo; l'animazione è cosmetica lato client (WorldAnimator).
]]
local Creatures = require(script.Parent.Parent.Catalog.Creatures)
local PartUtil = require(script.Parent.PartUtil)

local CreatureModel = {}

local function face(body, size, accent)
	local eyeR = size * 0.12
	for _, side in ipairs({ -1, 1 }) do
		local eye = PartUtil.Ball(eyeR * 2, Color3.fromRGB(30, 30, 40), body.CFrame * CFrame.new(side * size * 0.2, size * 0.1, -size * 0.42), body.Parent, { Name = "Eye" })
		PartUtil.Ball(eyeR * 0.8, Color3.new(1, 1, 1), eye.CFrame * CFrame.new(-side * eyeR * 0.3, eyeR * 0.4, -eyeR * 0.7), body.Parent, { Name = "EyeShine", Material = Enum.Material.Neon })
		-- guancia
		PartUtil.Part({
			Shape = Enum.PartType.Cylinder, Size = Vector3.new(0.1, size * 0.18, size * 0.18), Color = Color3.fromRGB(255, 160, 170), Transparency = 0.25,
			CFrame = body.CFrame * CFrame.new(side * size * 0.33, -size * 0.08, -size * 0.36) * CFrame.Angles(0, math.rad(90 + side * 25), 0),
			Parent = body.Parent, CanCollide = false, Name = "Cheek",
		})
	end
	-- bocca sorridente (piccolo cilindro scuro)
	PartUtil.Part({
		Shape = Enum.PartType.Cylinder, Size = Vector3.new(0.08, size * 0.08, size * 0.22), Color = Color3.fromRGB(70, 40, 60),
		CFrame = body.CFrame * CFrame.new(0, -size * 0.18, -size * 0.48) * CFrame.Angles(0, math.rad(90), 0),
		Parent = body.Parent, CanCollide = false, Name = "Mouth",
	})
end

local function familyFeature(def, body, size, color, accent)
	local parent = body.Parent
	local fam = def.Family
	if fam == "sole" then
		for i = 1, 8 do
			local a = (i / 8) * math.pi * 2
			local cf = body.CFrame * CFrame.Angles(0, 0, a) * CFrame.new(0, size * 0.75, 0)
			PartUtil.Part({ Size = Vector3.new(size * 0.16, size * 0.42, size * 0.1), Color = accent, Material = Enum.Material.Neon, CFrame = cf, Parent = parent, CanCollide = false, Name = "Ray", CastShadow = false })
		end
	elseif fam == "pioggia" then
		-- cappellino di nuvola
		PartUtil.Cloud(body.CFrame * CFrame.new(0, size * 0.62, 0), size * 0.22, parent, Color3.fromRGB(245, 248, 255), 0)
		-- codina a goccia
		PartUtil.Ball(size * 0.35, color, body.CFrame * CFrame.new(0, -size * 0.55, size * 0.1), parent, { Name = "Drop", Material = Enum.Material.Glass, Transparency = 0.2 })
		PartUtil.Emitter(body, { Color = accent, Rate = 3, Speed = NumberRange.new(1, 2), Acceleration = Vector3.new(0, -6, 0), Size = NumberSequence.new(0.18), Lifetime = NumberRange.new(0.5, 0.9), Spread = Vector2.new(30, 30), Name = "Drizzle" })
	elseif fam == "vento" then
		for i = 1, 3 do
			local a = i * 0.9
			local cf = body.CFrame * CFrame.new(math.cos(a) * size * 0.55, (i - 2) * size * 0.18, size * 0.45 + i * 0.12) * CFrame.Angles(0, a, math.rad(20))
			PartUtil.Part({ Size = Vector3.new(size * 0.55, size * 0.08, size * 0.12), Color = accent, Material = Enum.Material.Neon, Transparency = 0.25, CFrame = cf, Parent = parent, CanCollide = false, Name = "Swirl", CastShadow = false })
		end
		PartUtil.Emitter(body, { Color = accent, Rate = 4, Speed = NumberRange.new(1.5, 2.5), Acceleration = Vector3.new(0, 0.3, 0), Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.1), NumberSequenceKeypoint.new(0.5, 0.35), NumberSequenceKeypoint.new(1, 0) }), Lifetime = NumberRange.new(0.6, 1.1), Name = "Gust" })
	elseif fam == "aurora" then
		local segs = 7
		for i = 1, segs do
			local t = (i - 1) / (segs - 1)
			local a = math.rad(200 - t * 220)
			local c = color:Lerp(accent, t)
			local cf = body.CFrame * CFrame.new(math.cos(a) * size * 0.72, size * 0.25 + math.sin(a) * size * 0.55, 0) * CFrame.Angles(0, 0, a + math.rad(90))
			PartUtil.Part({ Size = Vector3.new(size * 0.14, size * 0.3, size * 0.18), Color = c, Material = Enum.Material.Neon, Transparency = 0.15, CFrame = cf, Parent = parent, CanCollide = false, Name = "Arc", CastShadow = false })
		end
	end
end

function CreatureModel.Build(creatureId, variantId, parent)
	local def = Creatures.Get(creatureId)
	if not def then
		return nil
	end
	local variant = Creatures.GetVariant(creatureId, variantId or "base") or def.Variants[1]
	local color = variant.Color
	local accent = def.Visual.Accent
	local size = def.Visual.Size

	local model = PartUtil.Model("Creature_" .. creatureId, nil)
	model:SetAttribute("CreatureId", creatureId)
	model:SetAttribute("Variant", variant.Id)
	model:SetAttribute("Behavior", def.Behavior)

	local body = PartUtil.Ball(size, color, CFrame.new(0, 0, 0), model, { Name = "Body", Material = Enum.Material.SmoothPlastic, CanQuery = true })
	model.PrimaryPart = body
	-- cuore luminoso interno (dà profondità)
	PartUtil.Ball(size * 0.55, accent, body.CFrame, model, { Name = "Core", Material = Enum.Material.Neon, Transparency = 0.55, CastShadow = false })

	face(body, size, accent)
	familyFeature(def, body, size, color, accent)

	local glow = def.Visual.Glow or 0.5
	PartUtil.Light(body, color, 0.6 + glow * 0.8, 8 + glow * 6)

	if def.Rarity == "leggendario" or def.Rarity == "raro" then
		local sparkles = Instance.new("Sparkles")
		sparkles.SparkleColor = accent
		sparkles.Enabled = def.Rarity == "leggendario"
		sparkles.Parent = body
		if def.Rarity == "raro" then
			PartUtil.Emitter(body, { Color = accent, Rate = 3, Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.25), NumberSequenceKeypoint.new(1, 0) }), Name = "Twinkle" })
		end
	end

	-- ombra morbida a terra (disco scuro trasparente)
	PartUtil.Part({
		Shape = Enum.PartType.Cylinder, Size = Vector3.new(0.05, size * 0.9, size * 0.9), Color = Color3.fromRGB(40, 60, 100), Transparency = 0.75,
		CFrame = CFrame.new(0, -2.45, 0) * CFrame.Angles(0, 0, math.rad(90)), Parent = model, CanCollide = false, Name = "Shadow", CastShadow = false,
	})

	if parent then
		model.Parent = parent
	end
	return model
end

return CreatureModel
