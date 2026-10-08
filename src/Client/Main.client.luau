--!nonstrict
--[[
	Main (client): crea la ScreenGui, avvia controller e pannelli, collega il menu.
]]
local Players = game:GetService("Players")
local StarterGui = game:GetService("StarterGui")
local GuiService = game:GetService("GuiService")
local UserInputService = game:GetService("UserInputService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage.Shared
local Strings = require(Shared.Strings)
local Net = require(Shared.Util.Net)

local Controllers = script.Parent.Controllers
local UIFolder = script.Parent.UI

local State = require(Controllers.State)
local Audio = require(Controllers.Audio)
local Build = require(Controllers.BuildController)
local RaidController = require(Controllers.RaidController)
local WorldAnimator = require(Controllers.WorldAnimator)
local Visuals = require(Controllers.Visuals)
local Tutorial = require(Controllers.TutorialController)

local UI = require(UIFolder.UI)
local Toast = require(UIFolder.Toast)
local HUD = require(UIFolder.HUD)
local BuildPanel = require(UIFolder.BuildPanel)
local CommissionPanel = require(UIFolder.CommissionPanel)
local AlbumPanel = require(UIFolder.AlbumPanel)
local CocoonPanel = require(UIFolder.CocoonPanel)
local GalleryPanel = require(UIFolder.GalleryPanel)
local ShopPanel = require(UIFolder.ShopPanel)
local SettingsPanel = require(UIFolder.SettingsPanel)
local RaidPanel = require(UIFolder.RaidPanel)
local DemoPanel = require(UIFolder.DemoPanel)

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")

-- disattiva la lista giocatori di default per lasciare spazio alla UI; chat resta
pcall(function()
	StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.PlayerList, false)
	StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false)
end)

local screenGui = Instance.new("ScreenGui")
screenGui.Name = "VivaioUI"
screenGui.ResetOnSpawn = false
screenGui.IgnoreGuiInset = false
screenGui.ZIndexBehavior = Enum.ZIndexBehavior.Global
screenGui.Parent = playerGui

-- scala per schermi piccoli (mobile-first)
local scale = Instance.new("UIScale")
scale.Parent = screenGui
local camera = workspace.CurrentCamera
while not camera do
	workspace:GetPropertyChangedSignal("CurrentCamera"):Wait()
	camera = workspace.CurrentCamera
end
local function updateScale()
	local w = camera.ViewportSize.X
	scale.Scale = math.clamp(w / 1280, 0.62, 1)
end
updateScale()
camera:GetPropertyChangedSignal("ViewportSize"):Connect(updateScale)

State.Init()
Audio.Init()
Toast.Init(screenGui)

local panels = {}
local function closeAll(except)
	for id, p in pairs(panels) do
		if id ~= except and p.Close then
			p.Close()
		end
	end
end

HUD.Init(screenGui, {
	OnMenu = function(id)
		if RaidPanel.IsActive() then
			Toast.Show("Termina l'incursione prima di aprire i menu", "warning")
			return
		end
		Audio.Play("Click")
		closeAll(id)
		local p = panels[id]
		if p then
			p.Toggle()
		end
	end,
})

BuildPanel.Init(screenGui)
CommissionPanel.Init(screenGui)
AlbumPanel.Init(screenGui)
CocoonPanel.Init(screenGui)
GalleryPanel.Init(screenGui)
ShopPanel.Init(screenGui)
SettingsPanel.Init(screenGui)
RaidPanel.Init(screenGui)
DemoPanel.Init(screenGui)
panels.build = BuildPanel
panels.board = CommissionPanel
panels.album = AlbumPanel
panels.cocoon = CocoonPanel
panels.gallery = GalleryPanel
panels.shop = ShopPanel
panels.settings = SettingsPanel
panels.raid = RaidPanel
panels.demo = { Open = DemoPanel.Open, Close = DemoPanel.Close, Toggle = DemoPanel.Open }

Build.Init()
WorldAnimator.Init()
Visuals.Init(screenGui, HUD)
Tutorial.Init(screenGui, HUD)
SettingsPanel.ReducedEffectsChanged = function(v)
	WorldAnimator.SetReduced(v)
end

RaidController.Init(function(name, payload)
	if name == "OpenPanel" then
		Audio.Play("Click")
		closeAll(payload.Panel)
		local p = panels[payload.Panel]
		if p then
			p.Open()
		end
	elseif name == "Emote" then
		Visuals.ShowEmote(payload.UserId, payload.Text)
	elseif name == "CocoonHatched" then
		Audio.Play("Success")
	else
		if name == "Start" then
			closeAll()
			Build.Stop()
		end
		RaidPanel.HandleEvent(name, payload)
	end
end)

Net.Event("Toast").OnClientEvent:Connect(function(message, kind)
	Toast.Show(message, kind)
	if kind == "warning" or kind == "error" then
		Audio.Play("Error", 1)
	end
end)

-- emote con il tasto T / pulsante su mobile gestito dalle Opzioni
UserInputService.InputBegan:Connect(function(input, processed)
	if processed then
		return
	end
	if input.KeyCode == Enum.KeyCode.T then
		Net.Fire("Emote")
	end
end)

State.OnReady(function()
	Toast.Show("Benvenuto in " .. Strings.Game .. "!", "success")
end)
