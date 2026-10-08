--!nonstrict
--[[
	Visuals: scie cosmetiche sui personaggi, targhette sopra la testa, emote, tema settimanale
	e cielo equipaggiato (illuminazione locale), effetto "scintille che volano" verso l'HUD.
]]
local Players = game:GetService("Players")
local Lighting = game:GetService("Lighting")
local TweenService = game:GetService("TweenService")
local Workspace = game:GetService("Workspace")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Cosmetics = require(Shared.Catalog.Cosmetics)
local Themes = require(Shared.Catalog.Themes)
local Net = require(Shared.Util.Net)
local PartUtil = require(Shared.Models.PartUtil)
local UI = require(script.Parent.Parent.UI.UI)
local State = require(script.Parent.State)

local Visuals = {}
local localPlayer = Players.LocalPlayer
local screenGui, hud
local themeParticles

-- ───────────────────────── scie e targhette ─────────────────────────

local function applyTrail(player, char)
	local hrp = char:FindFirstChild("HumanoidRootPart")
	if not hrp then
		return
	end
	local old = hrp:FindFirstChild("CosmeticTrail")
	if old then
		old:Destroy()
	end
	local trailId = player:GetAttribute("Trail")
	local c = trailId and Cosmetics.Get(trailId)
	if c and c.Data.Color then
		PartUtil.Emitter(hrp, { Name = "CosmeticTrail", Color = c.Data.Color, Rate = c.Data.Rate or 6, Speed = NumberRange.new(0.3, 1), Lifetime = NumberRange.new(0.6, 1.2), Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.35), NumberSequenceKeypoint.new(1, 0) }), Acceleration = Vector3.new(0, 1.5, 0) })
	end
end

local function applyNameplate(player, char)
	local head = char:FindFirstChild("Head")
	if not head then
		return
	end
	local old = head:FindFirstChild("CosmeticPlate")
	if old then
		old:Destroy()
	end
	local plateId = player:GetAttribute("Nameplate")
	local c = plateId and Cosmetics.Get(plateId)
	if c and c.Data.Text then
		local bb = PartUtil.Billboard(head, { Name = "CosmeticPlate", Size = UDim2.fromOffset(140, 26), Offset = Vector3.new(0, 3.2, 0), Text = "✦ " .. c.Data.Text .. " ✦", TextColor = c.Data.Color or Color3.new(1, 1, 1), MaxDistance = 60 })
		bb.AlwaysOnTop = false
	end
end

local function watchPlayer(player)
	local function onChar(char)
		task.wait(0.5)
		applyTrail(player, char)
		applyNameplate(player, char)
	end
	player.CharacterAdded:Connect(onChar)
	if player.Character then
		task.spawn(onChar, player.Character)
	end
	player:GetAttributeChangedSignal("Trail"):Connect(function()
		if player.Character then
			applyTrail(player, player.Character)
		end
	end)
	player:GetAttributeChangedSignal("Nameplate"):Connect(function()
		if player.Character then
			applyNameplate(player, player.Character)
		end
	end)
end

local function showEmote(userId, text)
	local p = Players:GetPlayerByUserId(userId)
	local head = p and p.Character and p.Character:FindFirstChild("Head")
	if not head then
		return
	end
	local bb, label = PartUtil.Billboard(head, { Name = "Emote", Size = UDim2.fromOffset(80, 80), Offset = Vector3.new(0, 4.5, 0), Text = text, MaxDistance = 80 })
	label.TextScaled = true
	TweenService:Create(bb, TweenInfo.new(1.6, Enum.EasingStyle.Quad), { StudsOffset = Vector3.new(0, 7, 0) }):Play()
	task.delay(1.4, function()
		TweenService:Create(label, TweenInfo.new(0.4), { TextTransparency = 1 }):Play()
		task.wait(0.45)
		bb:Destroy()
	end)
end

-- ───────────────────────── tema e cielo ─────────────────────────

local function applySkyAndTheme()
	local cos = State.Get("Cosmetics")
	local skyId = cos and cos.Equipped and cos.Equipped.sky or "sky_giorno"
	local sky = Cosmetics.Get(skyId) or Cosmetics.Get("sky_giorno")
	local info = State.Get("ServerInfo")
	local theme = info and Themes.ById[info.ThemeId]
	local clock = sky.Data.ClockTime or 13.5
	local tint = sky.Data.Tint or Color3.new(1, 1, 1)
	if theme then
		tint = tint:Lerp(theme.Visual.Tint, 0.5)
	end
	TweenService:Create(Lighting, TweenInfo.new(2), { ClockTime = clock, Ambient = sky.Data.Ambient or Lighting.Ambient }):Play()
	local cc = Lighting:FindFirstChild("ThemeCorrection")
	if cc then
		TweenService:Create(cc, TweenInfo.new(2), { TintColor = tint }):Play()
	end
	-- particelle del tema nell'hub
	if themeParticles then
		themeParticles:Destroy()
		themeParticles = nil
	end
	if theme and not (State.Get("Settings") or {}).ReducedEffects then
		themeParticles = PartUtil.Part({ Size = Vector3.new(220, 2, 220), Transparency = 1, CanCollide = false, CanQuery = false, CFrame = CFrame.new(0, 45, 0), Parent = Workspace, Name = "ThemeParticles" })
		local props = { Color = theme.Visual.ParticleColor, Rate = 25, Lifetime = NumberRange.new(4, 7), Speed = NumberRange.new(2, 5), LightEmission = 0.5, Name = "Theme" }
		if theme.Visual.Particle == "rain" then
			props.Acceleration = Vector3.new(0, -30, 0)
			props.Size = NumberSequence.new(0.15)
			props.Rate = 60
		elseif theme.Visual.Particle == "leaf" then
			props.Acceleration = Vector3.new(6, -3, 2)
			props.Size = NumberSequence.new(0.5)
		elseif theme.Visual.Particle == "ribbon" then
			props.Acceleration = Vector3.new(1, 0.5, 0)
			props.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.2), NumberSequenceKeypoint.new(0.5, 2.5), NumberSequenceKeypoint.new(1, 0) })
		else
			props.Acceleration = Vector3.new(0, -2, 0)
			props.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.6), NumberSequenceKeypoint.new(1, 0) })
		end
		local e = PartUtil.Emitter(themeParticles, props)
		e.EmissionDirection = Enum.NormalId.Bottom
	end
end

-- ───────────────────────── scintille verso l'HUD ─────────────────────────

local function sparkFx(worldPos, amount)
	if not screenGui or (State.Get("Settings") or {}).ReducedEffects then
		return
	end
	local camera = Workspace.CurrentCamera
	local screenPos, onScreen = camera:WorldToViewportPoint(worldPos)
	if not onScreen then
		return
	end
	local target = hud and hud.CardPosition("Exposed") or Vector2.new(200, 40)
	local n = math.clamp(math.floor(amount / 8) + 1, 1, 10)
	for i = 1, n do
		local orb = UI.Frame(screenGui, { Size = UDim2.fromOffset(14, 14), Position = UDim2.fromOffset(screenPos.X + math.random(-30, 30), screenPos.Y + math.random(-30, 30)), BackgroundColor3 = Color3.fromRGB(255, 220, 110), ZIndex = 60 })
		UI.Corner(orb, UDim.new(1, 0))
		UI.Stroke(orb, Color3.fromRGB(255, 250, 220), 2)
		task.delay(i * 0.04, function()
			local tw = TweenService:Create(orb, TweenInfo.new(0.55 + math.random() * 0.2, Enum.EasingStyle.Quad, Enum.EasingDirection.In), { Position = UDim2.fromOffset(target.X, target.Y), Size = UDim2.fromOffset(6, 6) })
			tw:Play()
			tw.Completed:Once(function()
				orb:Destroy()
			end)
		end)
	end
	local label = UI.Label(screenGui, "+" .. amount .. " ✦", { Size = UDim2.fromOffset(120, 30), Position = UDim2.fromOffset(screenPos.X - 60, screenPos.Y - 40), Font = UI.Theme.Font, TextSize = 22, TextColor3 = Color3.fromRGB(255, 220, 110), TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 60, TextStrokeTransparency = 0.4 })
	TweenService:Create(label, TweenInfo.new(0.9), { Position = UDim2.fromOffset(screenPos.X - 60, screenPos.Y - 100), TextTransparency = 1 }):Play()
	task.delay(1, function()
		label:Destroy()
	end)
end

function Visuals.Init(gui, hudModule)
	screenGui = gui
	hud = hudModule
	for _, p in ipairs(Players:GetPlayers()) do
		watchPlayer(p)
	end
	Players.PlayerAdded:Connect(watchPlayer)
	Net.Event("SparkFx").OnClientEvent:Connect(sparkFx)
	Net.Event("ThemeChanged").OnClientEvent:Connect(applySkyAndTheme)
	State.Changed:Connect(function(key)
		if key == "Cosmetics" or key == "ServerInfo" or key == "Settings" then
			applySkyAndTheme()
		end
	end)
	State.OnReady(applySkyAndTheme)
end

Visuals.ShowEmote = showEmote
return Visuals
