--!nonstrict
-- Template del profilo giocatore. Il DataService riconcilia i profili esistenti con questo.
local Config = require(script.Parent.Config)
local Cosmetics = require(script.Parent.Catalog.Cosmetics)

return function()
	return {
		Version = Config.DataVersion,
		Created = os.time(),
		LastSeen = os.time(),

		Sparks = {
			Exposed = 0, -- raccolte ma non depositate (sottraibili)
			Vault = 0, -- depositate (al sicuro)
			VaultLevel = 1,
		},
		Fragments = 0,
		StyleTokens = 0,

		PlotLevel = 1,
		-- Creature possedute: uid -> { Id, Variant, x, z (nil se in inventario), Buffer, LastTick }
		Creatures = {},
		OwnedCreatureIds = {},
		UnlockedVariants = {}, -- creatureId -> { variantId = true }
		NextCreatureUid = 1,

		Layout = { Modules = {} },
		LastValidLayout = { Modules = {} },
		LayoutVersion = 0,
		UnlockedModules = { corrente = true, muro_nube = true },
		UnlockedAlternatives = {}, -- moduleId -> { altId = true }
		ModuleAlternative = {}, -- moduleId -> altId scelto

		Decorations = {
			Owned = {},
			Placed = {}, -- { Id, x, z, Rot }
		},

		Cosmetics = {
			Owned = { skin_prato = true, sky_giorno = true, trail_nessuna = true, emote_saluto = true, plate_nessuna = true },
			Equipped = table.clone(Cosmetics.Defaults),
		},
		Pass = { Points = 0, ClaimedFree = {}, ClaimedPremium = {}, Premium = false },
		Founder = false,

		Commissions = { DayKey = "", List = {}, RerollsUsed = 0 },
		DailyStats = { DayKey = "" },
		WeeklyStats = { WeekIndex = -1 },
		WeeklyChallengeClaimed = {}, -- weekIndex -> true

		Album = { Claimed = {} },
		Mastery = {
			Collection = 0,
			Raid = 0,
			Defense = 0,
			ClaimedTiers = { Collection = 0, Raid = 0, Defense = 0 },
		},
		AutoDepositUnlocked = false,

		Cocoon = { Active = nil, Completed = 0 },

		Raid = {
			LossTimestamps = {},
			ShieldUntil = 0,
			RecentTargets = {}, -- key -> timestamp
			Attempts = 0,
			Successes = 0,
			Defended = 0,
			Lost = 0,
			RecentResults = {}, -- ultimi 10 esiti: 1 successo, 0 fallimento
			History = {}, -- riepiloghi (max 10)
			LastRaidAt = 0,
			AppliedInbox = {}, -- raidId -> true (idempotenza)
			AppliedInboxOrder = {},
		},

		Gallery = {
			Published = false,
			Likes = 0,
			LikesGiven = {}, -- key -> dayKey
			ShareCode = "",
		},

		Stats = {
			TotalCollected = 0,
			TotalDeposited = 0,
			TotalSpent = 0,
			RaidsDefended = 0,
			RaidsWon = 0,
			RaidsLost = 0,
			LayoutsPublished = 0,
			PlayTime = 0,
			Sessions = 0,
			FirstActionAt = nil,
		},

		Settings = {
			AudioEnabled = true,
			ReducedEffects = false,
			AutoDeposit = false,
			HideProfile = false,
			ShowName = true,
		},

		Tutorial = { Step = 1, CompletedOnce = false, Active = true },

		Ledger = {}, -- id ricompensa -> true (idempotenza acquisti/commissioni)
	}
end
