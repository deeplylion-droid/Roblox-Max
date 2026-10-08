--!nonstrict
local RunService = game:GetService("RunService")

local Logger = {}
local verbose = RunService:IsStudio()

function Logger.Info(tag, ...)
	if verbose then
		print(string.format("[%s]", tag), ...)
	end
end

function Logger.Warn(tag, ...)
	warn(string.format("[%s]", tag), ...)
end

function Logger.Audit(tag, player, action, details)
	-- Log strutturato per rollback mirato/analisi (sezione 9 del GDD)
	local line = string.format("[AUDIT][%s] %s (%d) %s %s", tag, player and player.Name or "server", player and player.UserId or 0, action, details or "")
	print(line)
end

return Logger
