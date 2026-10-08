--!nonstrict
-- Temi settimanali: modificatore visivo + sfida facoltativa con premio cosmetico/gettoni.
export type Theme = {
	Id: string,
	Name: string,
	Description: string,
	Visual: { Tint: Color3, Ambient: Color3, ParticleColor: Color3, Particle: string, ClockTime: number },
	Challenge: { Text: string, Stat: string, Target: number, Reward: { Tokens: number?, Cosmetic: string? } },
}

local list: { Theme } = {
	{
		Id = "aurora", Name = "Settimana dell'Aurora", Description = "Veli verdi e viola attraversano il cielo dell'hub.",
		Visual = { Tint = Color3.fromRGB(205, 190, 255), Ambient = Color3.fromRGB(120, 130, 190), ParticleColor = Color3.fromRGB(150, 255, 210), Particle = "ribbon", ClockTime = 18.5 },
		Challenge = { Text = "Deposita 1.500 scintille questa settimana", Stat = "WeeklyDeposited", Target = 1500, Reward = { Tokens = 25 } },
	},
	{
		Id = "monsone", Name = "Monsone gentile", Description = "Pioggia luminosa e riflessi perlati.",
		Visual = { Tint = Color3.fromRGB(200, 215, 235), Ambient = Color3.fromRGB(140, 150, 175), ParticleColor = Color3.fromRGB(170, 210, 255), Particle = "rain", ClockTime = 15 },
		Challenge = { Text = "Completa 6 incursioni questa settimana (anche simulate)", Stat = "WeeklyRaids", Target = 6, Reward = { Tokens = 25 } },
	},
	{
		Id = "alisei", Name = "Settimana degli Alisei", Description = "Correnti di foglie e nastri di vento.",
		Visual = { Tint = Color3.fromRGB(215, 250, 235), Ambient = Color3.fromRGB(140, 175, 170), ParticleColor = Color3.fromRGB(190, 245, 220), Particle = "leaf", ClockTime = 11 },
		Challenge = { Text = "Pubblica 3 layout diversi questa settimana", Stat = "WeeklyLayouts", Target = 3, Reward = { Cosmetic = "skin_alisei" } },
	},
	{
		Id = "solstizio", Name = "Solstizio dorato", Description = "Luce lunga e calda su tutto il vivaio.",
		Visual = { Tint = Color3.fromRGB(255, 230, 190), Ambient = Color3.fromRGB(190, 160, 130), ParticleColor = Color3.fromRGB(255, 220, 130), Particle = "spark", ClockTime = 17 },
		Challenge = { Text = "Completa 8 commissioni questa settimana", Stat = "WeeklyCommissions", Target = 8, Reward = { Cosmetic = "plate_meteorologo" } },
	},
}

local Themes = { List = list, ById = {} }
for _, t in ipairs(list) do
	Themes.ById[t.Id] = t
end

function Themes.ForWeek(weekIndex)
	return list[(weekIndex % #list) + 1]
end

return Themes
