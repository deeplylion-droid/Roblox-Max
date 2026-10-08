--!nonstrict
-- Tipi condivisi (documentazione + supporto editor)
export type Cell = { x: number, z: number }

export type CreatureInstance = {
	Id: string,
	Variant: string,
	x: number?,
	z: number?,
	Buffer: number,
	LastTick: number,
}

export type RaidTarget = {
	Key: string,
	Name: string,
	Tier: number,
	Difficulty: number, -- 1..5
	ExposedEstimate: number,
	MaxTake: number,
	Simulated: boolean,
	ModuleCount: number,
}

export type RaidSummary = {
	Success: boolean,
	Take: number,
	Participation: number,
	Mastery: number,
	Feedback: { string },
	Duration: number,
	Simulated: boolean,
	Test: boolean,
}

return {}
