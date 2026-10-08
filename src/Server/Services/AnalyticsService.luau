--!nonstrict
--[[
	AnalyticsService: metriche del GDD §8 (completamento tutorial, prima azione, raid,
	abbandono dopo perdita). Usa AnalyticsService di Roblox con pcall; in Studio stampa.
]]
local RobloxAnalytics = game:GetService("AnalyticsService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)

local Analytics = {}
local lastLoss = {} -- player -> timestamp dell'ultima perdita da raid

function Analytics.Log(player, eventName, value)
	if RunService:IsStudio() then
		print(string.format("[Analytics] %s %s %s", player and player.Name or "-", eventName, tostring(value)))
	end
	pcall(function()
		RobloxAnalytics:LogCustomEvent(player, eventName, value or 1)
	end)
end

function Analytics.Funnel(player, funnelName, step)
	if RunService:IsStudio() then
		print(string.format("[Analytics] funnel %s step %d (%s)", funnelName, step, player.Name))
	end
	pcall(function()
		RobloxAnalytics:LogFunnelStepEvent(player, funnelName, nil, step, "step_" .. step)
	end)
end

function Analytics.Init() end

function Analytics.Start()
	EventBus.On("RaidCompleted", function(player, summary)
		Analytics.Log(player, summary.Success and "raid_success" or "raid_fail", summary.Duration)
	end)
	EventBus.On("RaidLost", function(player, amount)
		lastLoss[player] = os.time()
		Analytics.Log(player, "raid_loss_received", amount)
	end)
	EventBus.On("RaidDefended", function(player, amount)
		Analytics.Log(player, "raid_defended", amount)
	end)
	EventBus.On("LayoutPublished", function(player, count)
		Analytics.Log(player, "layout_published", count)
	end)
	EventBus.On("CommissionClaimed", function(player)
		Analytics.Log(player, "commission_claimed", 1)
	end)
	Players.PlayerRemoving:Connect(function(player)
		local t = lastLoss[player]
		if t and os.time() - t < 120 then
			Analytics.Log(player, "quit_within_2min_of_loss", os.time() - t)
		end
		lastLoss[player] = nil
	end)
end

return Analytics
