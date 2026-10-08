--!nonstrict
-- Schermata di caricamento leggera con suggerimenti del GDD, rimossa quando lo stato è pronto.
local ReplicatedFirst = game:GetService("ReplicatedFirst")
local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")
ReplicatedFirst:RemoveDefaultLoadingScreen()

local gui = Instance.new("ScreenGui")
gui.Name = "LoadingScreen"
gui.IgnoreGuiInset = true
gui.DisplayOrder = 100
gui.ResetOnSpawn = false
gui.Parent = playerGui

local bg = Instance.new("Frame")
bg.Size = UDim2.fromScale(1, 1)
bg.BackgroundColor3 = Color3.fromRGB(176, 214, 255)
bg.BorderSizePixel = 0
bg.Parent = gui
local grad = Instance.new("UIGradient")
grad.Color = ColorSequence.new(Color3.fromRGB(120, 170, 240), Color3.fromRGB(230, 240, 255))
grad.Rotation = 90
grad.Parent = bg

local title = Instance.new("TextLabel")
title.Size = UDim2.new(1, 0, 0, 80)
title.Position = UDim2.new(0, 0, 0.36, 0)
title.BackgroundTransparency = 1
title.Font = Enum.Font.FredokaOne
title.TextScaled = true
title.TextColor3 = Color3.new(1, 1, 1)
title.TextStrokeTransparency = 0.6
title.Text = "Il Vivaio delle Nuvole"
title.Parent = bg

local sub = Instance.new("TextLabel")
sub.Size = UDim2.new(1, 0, 0, 30)
sub.Position = UDim2.new(0, 0, 0.36, 90)
sub.BackgroundTransparency = 1
sub.Font = Enum.Font.GothamMedium
sub.TextSize = 20
sub.TextColor3 = Color3.fromRGB(40, 60, 100)
sub.Text = "Preparo le nuvole…"
sub.Parent = bg

local tip = Instance.new("TextLabel")
tip.Size = UDim2.new(0.8, 0, 0, 60)
tip.Position = UDim2.new(0.1, 0, 0.7, 0)
tip.BackgroundTransparency = 1
tip.Font = Enum.Font.GothamMedium
tip.TextSize = 17
tip.TextWrapped = true
tip.TextColor3 = Color3.fromRGB(40, 60, 100)
tip.Parent = bg

local ok, Strings = pcall(function()
	return require(ReplicatedStorage:WaitForChild("Shared", 10):WaitForChild("Strings", 10))
end)
if ok and Strings then
	tip.Text = Strings.LoadingTip[math.random(1, #Strings.LoadingTip)]
end

-- nuvolette animate
for i = 1, 6 do
	local cloud = Instance.new("Frame")
	cloud.Size = UDim2.fromOffset(120 + i * 15, 44)
	cloud.Position = UDim2.new(math.random() * 0.9, 0, 0.1 + i * 0.1, 0)
	cloud.BackgroundColor3 = Color3.new(1, 1, 1)
	cloud.BackgroundTransparency = 0.25
	cloud.BorderSizePixel = 0
	cloud.Parent = bg
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(1, 0)
	c.Parent = cloud
	TweenService:Create(cloud, TweenInfo.new(14 + i * 3, Enum.EasingStyle.Linear, Enum.EasingDirection.InOut, -1, true), { Position = UDim2.new(cloud.Position.X.Scale + 0.1, 0, cloud.Position.Y.Scale, 0) }):Play()
end

-- attende la UI principale o un timeout
local t0 = os.clock()
while os.clock() - t0 < 25 do
	local main = playerGui:FindFirstChild("VivaioUI")
	if main and main:FindFirstChild("HUD") then
		break
	end
	task.wait(0.2)
end
task.wait(0.6)
TweenService:Create(bg, TweenInfo.new(0.6), { BackgroundTransparency = 1 }):Play()
for _, d in ipairs(bg:GetDescendants()) do
	if d:IsA("TextLabel") then
		TweenService:Create(d, TweenInfo.new(0.5), { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
	elseif d:IsA("Frame") then
		TweenService:Create(d, TweenInfo.new(0.5), { BackgroundTransparency = 1 }):Play()
	end
end
task.wait(0.7)
gui:Destroy()
