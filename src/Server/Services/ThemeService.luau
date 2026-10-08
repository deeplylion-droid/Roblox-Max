--!nonstrict
--[[
	ThemeService: tema settimanale (modificatore visivo + sfida facoltativa con premio).
	Il tema cambia ogni lunedì; le creature e i sistemi restano invariati.
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Themes = require(Shared.Catalog.Themes)
local TimeUtil = require(Shared.Util.TimeUtil)
local Net = require(Shared.Util.Net)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)

local ThemeService = {}
local currentWeek = TimeUtil.WeekIndex()

function ThemeService.CurrentThemeId()
	return Themes.ForWeek(currentWeek).Id
end

function ThemeService.Progress(profile)
	local theme = Themes.ForWeek(currentWeek)
	local weekly = Registry.Get("StatsService").Weekly(profile)
	return {
		ThemeId = theme.Id,
		Progress = math.min(weekly[theme.Challenge.Stat] or 0, theme.Challenge.Target),
		Target = theme.Challenge.Target,
		Claimed = profile.WeeklyChallengeClaimed[tostring(currentWeek)] == true,
		SecondsToNextWeek = TimeUtil.SecondsToNextWeek(),
	}
end

function ThemeService.Claim(player)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	local theme = Themes.ForWeek(currentWeek)
	local weekly = Registry.Get("StatsService").Weekly(profile)
	if (weekly[theme.Challenge.Stat] or 0) < theme.Challenge.Target then
		return false, "Sfida non completata"
	end
	local key = tostring(currentWeek)
	if profile.WeeklyChallengeClaimed[key] then
		return false, "Già riscosso"
	end
	profile.WeeklyChallengeClaimed[key] = true
	local r = theme.Challenge.Reward
	if r.Tokens then
		Registry.Get("EconomyService").GrantTokens(player, profile, r.Tokens, "weekly")
	end
	if r.Cosmetic then
		Registry.Get("ShopService").GrantCosmetic(player, profile, r.Cosmetic, "weekly")
	end
	Registry.Get("PlayerService").Sync(player, "WeeklyChallengeClaimed", "ServerInfo")
	Registry.Get("PlayerService").Sound(player, "Success")
	Registry.Get("PlayerService").Toast(player, "Sfida settimanale completata!", "success")
	return true
end

function ThemeService.Init()
	Net.Function("ClaimWeeklyChallenge").OnServerInvoke = ThemeService.Claim
end

function ThemeService.Start()
	EventBus.On("WeeklyStatDelta", function(player)
		Registry.Get("PlayerService").Sync(player, "ServerInfo")
	end)
	task.spawn(function()
		while true do
			task.wait(60)
			local w = TimeUtil.WeekIndex()
			if w ~= currentWeek then
				currentWeek = w
				for player in pairs(Registry.Get("DataService").GetAll()) do
					Net.Event("ThemeChanged"):FireClient(player, ThemeService.CurrentThemeId())
					Registry.Get("PlayerService").Sync(player, "ServerInfo")
				end
			end
		end
	end)
end

return ThemeService
