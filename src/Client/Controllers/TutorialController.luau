--!nonstrict
-- Tutorial guidato in 5 passi con banner, evidenziazione del menu e scelta della decorazione.
local Players = game:GetService("Players")
local Workspace = game:GetService("Workspace")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Decorations = require(Shared.Catalog.Decorations)
local Net = require(Shared.Util.Net)
local PartUtil = require(Shared.Models.PartUtil)
local DecorationModel = require(Shared.Models.DecorationModel)
local UI = require(script.Parent.Parent.UI.UI)
local Toast = require(script.Parent.Parent.UI.Toast)
local State = require(script.Parent.State)

local Tutorial = {}
local C = UI.Colors
local player = Players.LocalPlayer
local banner, bannerText, stepLabel, skipButton, choicePanel
local beacon
local hud

local HIGHLIGHT = { [1] = "build", [2] = nil, [3] = "build", [4] = "raid", [5] = nil }

local function clearBeacon()
	if beacon then
		beacon:Destroy()
		beacon = nil
	end
end

local function placeBeacon(position)
	clearBeacon()
	beacon = PartUtil.Part({ Size = Vector3.new(1.2, 40, 1.2), Color = Color3.fromRGB(255, 220, 110), Material = Enum.Material.Neon, Transparency = 0.5, CanCollide = false, CanQuery = false, CFrame = CFrame.new(position + Vector3.new(0, 20, 0)), Parent = Workspace, Name = "TutorialBeacon", CastShadow = false })
end

local function myPlot()
	local plots = Workspace:FindFirstChild("Plots")
	if not plots then
		return nil
	end
	for _, m in ipairs(plots:GetChildren()) do
		if m:GetAttribute("OwnerUserId") == player.UserId then
			return m
		end
	end
	return nil
end

local function updateBeacon(step)
	clearBeacon()
	local plot = myPlot()
	if step == 2 and plot then
		local vault = plot.Structure:FindFirstChild("VaultBody")
		if vault then
			placeBeacon(vault.Position)
		end
	elseif step == 4 and plot then
		local pad = plot.Structure:FindFirstChild("HubPad")
		if pad and player:GetAttribute("Location") == "home" then
			placeBeacon(pad.Position)
		else
			local world = Workspace:FindFirstChild("World")
			local hub = world and world:FindFirstChild("Hub")
			local portal = hub and hub:FindFirstChild("PortaleIncursioni")
			if portal and portal:FindFirstChild("Base") then
				placeBeacon(portal.Base.Position)
			end
		end
	end
end

local function showChoice()
	if choicePanel then
		return
	end
	choicePanel = UI.Panel(banner.Parent, "🎁 Scegli una decorazione gratuita", UDim2.new(0.6, 0, 0.6, 0))
	local content = choicePanel.Content
	UI.Grid(content, UDim2.new(0.5, -10, 1, -10), 10)
	for i, id in ipairs(Config.Tutorial.FreeDecorationChoices) do
		local def = Decorations.ById[id]
		local card = UI.Card(content, { LayoutOrder = i })
		UI.Viewport(card, DecorationModel.Build(id, nil, false), { Size = UDim2.new(1, -16, 0.55, 0), Position = UDim2.fromOffset(8, 8) })
		UI.Label(card, def.Name, { Font = UI.Theme.Font, TextSize = 20, Size = UDim2.new(1, -16, 0, 28), Position = UDim2.new(0, 8, 0.55, 12), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
		UI.Label(card, def.Description, { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, -16, 0, 36), Position = UDim2.new(0, 8, 0.55, 40), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
		local b = UI.Button(card, "Scelgo questa", function()
			local ok, msg = Net.Invoke("TutorialAdvance", 5, id)
			if ok then
				choicePanel:Close()
				choicePanel.Overlay:Destroy()
				choicePanel = nil
			else
				Toast.Show(msg or Strings.Error, "warning")
			end
		end, { Size = UDim2.new(1, -16, 0, 46), Position = UDim2.new(0, 8, 1, -54), Color = C.Success })
		b.ZIndex = 13
	end
	choicePanel.CloseButton.Visible = false
	choicePanel:Open()
end

local function apply(step, active)
	for _, id in pairs({ "build", "raid" }) do
		hud.Highlight(id, false)
	end
	if not active or step > Config.Tutorial.Steps then
		banner.Visible = false
		clearBeacon()
		return
	end
	banner.Visible = true
	stepLabel.Text = string.format("Tutorial %d / %d", step, Config.Tutorial.Steps)
	bannerText.Text = Strings.Tutorial[step] or ""
	local tut = State.Get("Tutorial") or {}
	skipButton.Visible = tut.CompletedOnce == true
	if HIGHLIGHT[step] then
		hud.Highlight(HIGHLIGHT[step], true)
	end
	updateBeacon(step)
	if step == 5 then
		showChoice()
	end
end

function Tutorial.Init(screenGui, hudModule)
	hud = hudModule
	banner = UI.Frame(screenGui, { Name = "TutorialBanner", BackgroundColor3 = C.PanelDark, BackgroundTransparency = 0.1, Size = UDim2.new(0, 620, 0, 74), Position = UDim2.new(0.5, 0, 1, -100), AnchorPoint = Vector2.new(0.5, 1), Visible = false, ZIndex = 25 })
	UI.Corner(banner, UDim.new(0, 18))
	UI.Stroke(banner, C.Accent, 2)
	stepLabel = UI.Label(banner, "", { Size = UDim2.fromOffset(160, 20), Position = UDim2.fromOffset(14, 6), TextColor3 = C.Accent, Font = UI.Theme.FontBold, TextSize = 13, ZIndex = 26 })
	bannerText = UI.Label(banner, "", { Size = UDim2.new(1, -170, 0, 44), Position = UDim2.fromOffset(14, 26), TextColor3 = C.TextOnDark, TextSize = 15, ZIndex = 26, TextYAlignment = Enum.TextYAlignment.Top })
	skipButton = UI.Button(banner, Strings.TutorialSkip, function()
		local ok, msg = Net.Invoke("TutorialSkip")
		if not ok then
			Toast.Show(msg or Strings.Error, "warning")
		end
	end, { Size = UDim2.fromOffset(130, 36), Position = UDim2.new(1, -142, 0.5, -18), Color = C.TextMuted, TextSize = 13, Visible = false })
	skipButton.ZIndex = 26

	Net.Event("TutorialStep").OnClientEvent:Connect(function(step, active)
		apply(step, active)
	end)
	State.Observe("Tutorial", function(t)
		apply(t.Step, t.Active)
	end)
	player:GetAttributeChangedSignal("Location"):Connect(function()
		local t = State.Get("Tutorial")
		if t and t.Active then
			updateBeacon(t.Step)
		end
	end)
end

return Tutorial
