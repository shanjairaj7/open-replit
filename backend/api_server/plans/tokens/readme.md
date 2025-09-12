Model cost (assumed IO split for sizing): 80% input / 20% output

Effective model cost used: $0.00000089 per token ( = 0.8×($0.80/1e6) + 0.2×($1.25/1e6) )

Plans / prices: $25 / $49 / $99 / $149 / $200

Credits per plan: 100 / 250 / 500 / 750 / 1000

Margin targets per plan: 15% / 18% / 22% / 26% / 30% (ramped as requested)

Overage markup: 2.5× on provider cost per credit (yields a user-friendly extra-run price ≈ $1.33 for a typical internal run)

Final tier table (exact, locked-in)

All token numbers rounded to whole tokens.

Tier	Price	Credits	Tokens included	Tokens / credit	Provider cost	Cost/credit	Gross	Margin	≈ internal iters (600k tokens)
Base	$25	100	23,876,404	238,764	$21.25	$0.2125	$3.75	15.0%	39.8
Bronze	$49	250	45,146,067	180,584	$40.18	$0.1607	$8.82	18.0%	75.2
Silver	$99	500	86,764,045	173,528	$77.22	$0.1544	$21.78	22.0%	144.6
Gold	$149	750	123,887,640	165,184	$110.26	$0.1470	$38.74	26.0%	206.5
Platinum	$200	1000	157,303,371	157,303	$140.00	$0.1400	$60.00	30.0%	262.2

How each value was computed (step-by-step math):

cost_per_token = 0.8*(0.80/1_000_000) + 0.2*(1.25/1_000_000) = 0.00000089 $/token.

For each tier:

provider_allowed = price × (1 − target_margin)
Example (Base): 21.25 = 25 × (1 − 0.15).

tokens_included = provider_allowed / cost_per_token
Example (Base): 21.25 / 0.00000089 ≈ 23,876,404 tokens.

tokens_per_credit = tokens_included / credits
Example (Base): 23,876,404 / 100 ≈ 238,764 tokens/credit.

provider_cost_per_credit = provider_allowed / credits
Example (Base): 21.25 / 100 = $0.2125 / credit.

gross = price − provider_allowed (obvious).

internal iterations metric ≈ tokens_included / 600,000.

Overage:

overage_price_per_credit = provider_cost_per_credit × markup (2.5)
Example (Base): 0.2125 × 2.5 = $0.53125 / credit.

credits_for_a_600k_run = 600,000 / tokens_per_credit
Example (Base): 600,000 / 238,764 ≈ 2.513 credits.

overage_cost_for_600k_run = credits_for_a_600k_run × overage_price_per_credit ≈ $1.33 (same ~ $1.33 across tiers thanks to the math).

One-line rules / UX decisions to implement

User-facing unit = credits only. (Never show tokens unless user asks.)

100 / 250 / 500 / 750 / 1000 credit packs at the prices above.

Credits are replenished monthly per plan.

Overage behavior: if user runs out of plan credits, charge overage_price_per_credit (per-tier computed), or charge equivalent “extra run” price shown as ~$1.33 per typical run in tooltip/UI.

Instrumentation: always log measured input_tokens and output_tokens for each call to compute exact provider cost. Recompute cost_per_token every 2 weeks; if it drifts >5%, adjust prices or overage.

Exact per-tier overage numbers (for integration)
Tier	provider_cost_per_credit	overage_price_per_credit (×2.5)	credits used for 600k run	overage cost for 600k run
Base	$0.2125	$0.53125	2.513	$1.33
Bronze	$0.1607	$0.40175	3.323	$1.33
Silver	$0.1544	$0.38600	3.459	$1.33
Gold	$0.1470	$0.36750	3.633	$1.33
Platinum	$0.1400	$0.35000	3.814	$1.33

Practical note: because tokens_per_credit scales with provider cost per credit, a 600k internal run ends up costing ~3–2.5 credits depending on tier, and with the 2.5× markup the out-of-plan run cost stays ~ $1.33 across tiers. That’s a simple, predictable UX.

Drop-in billing code (JS-style) — exact tier values embedded
// Config (locked-in)
const COST_PER_TOKEN = 0.00000089; // effective, 80/20 IO split
const MARKUP = 2.5;

const TIERS = {
  Base:     { price:25,  credits:100,  providerAllowed: 21.25, tokens: 23876404 },
  Bronze:   { price:49,  credits:250,  providerAllowed: 40.18, tokens: 45146067 },
  Silver:   { price:99,  credits:500,  providerAllowed: 77.22, tokens: 86764045 },
  Gold:     { price:149, credits:750,  providerAllowed:110.26, tokens:123887640 },
  Platinum: { price:200, credits:1000, providerAllowed:140.00, tokens:157303371 }
};

function tokensPerCredit(tier){ return TIERS[tier].tokens / TIERS[tier].credits; }
function providerCostPerCredit(tier){ return TIERS[tier].providerAllowed / TIERS[tier].credits; }
function overagePricePerCredit(tier){ return providerCostPerCredit(tier) * MARKUP; }

// converts measured input/output tokens into credits used and provider cost
function computeRequestCost(measuredInputTokens, measuredOutputTokens, tier){
  const tokens = measuredInputTokens + measuredOutputTokens;
  const creditsUsed = tokens / tokensPerCredit(tier);
  const providerCost = measuredInputTokens*(0.8/1e6) + measuredOutputTokens*(1.25/1e6); // exact per-call
  return { tokens, creditsUsed, providerCost };
}

// billing flow (simplified)
function billRequest(user, measuredInputTokens, measuredOutputTokens, tier){
  const { tokens, creditsUsed, providerCost } = computeRequestCost(measuredInputTokens, measuredOutputTokens, tier);
  if(user.credits >= creditsUsed){
    user.credits -= creditsUsed;
    return { charged: 0, providerCost, creditsUsed };
  } else {
    const creditsFromPlan = Math.max(0, user.credits);
    const creditsOver = creditsUsed - creditsFromPlan;
    user.credits = 0;
    const overageCharge = creditsOver * overagePricePerCredit(tier);
    return { charged: overageCharge, providerCost, creditsUsed, creditsOver };
  }
}

User-facing UI copy (ready-to-drop)

Dashboard header: “Credits: 100 (Base plan) — 1 credit = plan-specific token allotment”

Tooltip: “Each plan converts credits → tokens differently to meet margin targets. Example: Base plan: 1 credit ≈ 238,764 tokens.”

Before an action: “This action will use ~2.5 credits (estimated). You have 10 credits left.”

If over quota: “You’ve used your plan credits. Extra run costs ≈ $1.33 (or buy credits).”

Billing page: list per-tier credits and tokens included (use numbers from the final table).

Operational checklist (do this first)

Wire measured input_tokens and output_tokens for every call into your analytics.

Start with the locked table above. Launch.

After 2 weeks, recompute cost_per_token from real IO ratios; adjust MARKUP or tiers only if provider cost changes materially.

If you want to keep simple legal text, show tokens included rounded (+/−) and label “approximate — actual usage billed in credits”.
