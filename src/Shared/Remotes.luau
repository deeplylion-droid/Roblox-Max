--!nonstrict
-- Elenco dei remoti. Il server li crea in ReplicatedStorage.Remotes; il client li attende.
return {
	Events = {
		-- server → client
		"StateSync", -- (key, value) aggiornamento di una sezione dello stato
		"Toast", -- (message, kind)
		"PlaySound", -- (soundKey)
		"SparkFx", -- (fromPos, toPos, amount)
		"RaidEvent", -- (eventName, payload)
		"TutorialStep", -- (step)
		"ThemeChanged", -- (themeId)
		-- client → server
		"CollectAll",
		"DepositAll",
		"ClientReady",
		"SetSetting", -- (key, value)
		"RaidAbort",
		"Emote",
	},
	Functions = {
		"GetState", -- () -> full state
		"Collect", -- (creatureUid) -> ok, msg
		"Deposit", -- () -> ok, msg
		"UpgradeVault",
		"UpgradePlot",
		"PlaceCreature", -- (uid, x, z)
		"RemoveCreature", -- (uid)
		"SetVariant", -- (uid, variantId)
		"SaveLayout", -- (layout) -> ok, msg
		"UnlockModule", -- (moduleId)
		"SetModuleAlternative", -- (moduleId, altId)
		"PlaceDecoration", -- (decoId, x, z, rot)
		"RemoveDecoration", -- (index)
		"RequestRaidTargets", -- () -> list
		"StartRaid", -- (targetKey) -> ok, msg
		"StartLayoutTest", -- () -> ok, msg
		"GetCommissions",
		"ClaimCommission", -- (index)
		"RerollCommission", -- (index)
		"ClaimAlbumMilestone", -- (milestoneId)
		"GetCocoonPreview", -- (family)
		"StartCocoon", -- (family)
		"GetGallery", -- () -> list
		"VisitVivaio", -- (key)
		"LikeVivaio", -- (key)
		"ImportLayoutCode", -- (code)
		"ReturnHome",
		"BuyCosmetic", -- (id)
		"EquipCosmetic", -- (id)
		"ClaimPassTier", -- (tier)
		"TutorialAdvance", -- (step, payload)
		"TutorialSkip",
		"ClaimWeeklyChallenge",
		"PromptPurchase", -- (cosmeticId)
	},
}
