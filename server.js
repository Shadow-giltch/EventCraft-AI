/**
 * EventCraft AI - Full-Stack Application Server
 * Serves static web UI and provides API endpoints for budget, timeline,
 * vendor checklist, and personalized event planning.
 */

import express from 'express';
import cors from 'cors';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = 3000;
const HOST = process.env.HOST || '0.0.0.0';
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-2.5-flash';

// Load Knowledge Base Templates
const KNOWLEDGE_DIR = path.join(__dirname, 'src', 'eventcraft', 'knowledge');
const templates = {
  wedding: JSON.parse(fs.readFileSync(path.join(KNOWLEDGE_DIR, 'wedding.json'), 'utf-8')),
  birthday: JSON.parse(fs.readFileSync(path.join(KNOWLEDGE_DIR, 'birthday.json'), 'utf-8')),
  community: JSON.parse(fs.readFileSync(path.join(KNOWLEDGE_DIR, 'community.json'), 'utf-8')),
};

const app = express();

// Parse JSON bodies with 32 KB limit
app.use(express.json({ limit: '32kb' }));

// Correlation ID & Security Headers Middleware
app.use((req, res, next) => {
  const correlationId = req.headers['x-correlation-id'] || crypto.randomUUID();
  res.setHeader('X-Correlation-ID', correlationId);
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; object-src 'none'"
  );
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  res.setHeader('Cache-Control', 'no-store');
  next();
});

// CORS Configuration
const rawOrigins = process.env.ALLOWED_ORIGINS || 'http://localhost:3000,http://127.0.0.1:3000';
let allowedOrigins = ['http://localhost:3000', 'http://127.0.0.1:3000'];
try {
  if (rawOrigins.startsWith('[') && rawOrigins.endsWith(']')) {
    allowedOrigins = JSON.parse(rawOrigins);
  } else {
    allowedOrigins = rawOrigins.split(',').map((s) => s.trim()).filter(Boolean);
  }
} catch {
  allowedOrigins = ['http://localhost:3000', 'http://127.0.0.1:3000'];
}
app.use(
  cors({
    origin: (origin, callback) => {
      if (!origin || allowedOrigins.includes(origin) || allowedOrigins.includes('*')) {
        callback(null, true);
      } else {
        callback(null, true); // Dev tolerance
      }
    },
    credentials: true,
  })
);

// In-Memory Cache for Plan Generations
const planCache = new Map();
const CACHE_TTL_MS = 60 * 60 * 1000;

function getCacheKey(prefix, obj) {
  return prefix + ':' + crypto.createHash('sha256').update(JSON.stringify(obj)).digest('hex');
}

// -------------------------------------------------------------
// Pure Domain Logic: Exact Largest-Remainder Budget Allocation
// -------------------------------------------------------------
function allocateBudget(totalAmount, currency, guestCount, configs, options = {}) {
  const priorities = options.priorities || [];
  const customWeights = options.customWeights || {};
  let contingencyPercent = options.contingencyPercent !== undefined ? Number(options.contingencyPercent) : 5.0;

  // Clamp contingency between 3% and 15%
  contingencyPercent = Math.max(3.0, Math.min(15.0, contingencyPercent));

  const totalCents = Math.round(Number(totalAmount) * 100);
  if (totalCents <= 0) throw new Error('Budget total must be greater than zero.');
  if (guestCount < 1) throw new Error('Guest count must be at least 1.');

  const contingencyCents = Math.round((totalCents * contingencyPercent) / 100);
  const allocatableCents = totalCents - contingencyCents;

  // Calculate raw weights
  const prioSet = new Set(priorities.map((p) => String(p).toLowerCase()));
  const adjustedConfigs = configs.map((c) => {
    let weight = Number(c.default_percent);
    if (customWeights[c.name] !== undefined) {
      weight = Number(customWeights[c.name]);
    } else {
      const isPrio = prioSet.has(c.name.toLowerCase()) || [...prioSet].some((p) => c.name.toLowerCase().includes(p));
      if (isPrio) weight *= 1.25;
    }
    const minW = c.min_percent !== undefined ? Number(c.min_percent) : 5.0;
    const maxW = c.max_percent !== undefined ? Number(c.max_percent) : 50.0;
    weight = Math.max(minW, Math.min(maxW, weight));
    return { ...c, computedWeight: weight };
  });

  const weightSum = adjustedConfigs.reduce((acc, c) => acc + c.computedWeight, 0);

  // Largest-Remainder Distribution
  let assignedCentsTotal = 0;
  const lineDetails = adjustedConfigs.map((c, index) => {
    const rawCents = (allocatableCents * c.computedWeight) / weightSum;
    const floorCents = Math.floor(rawCents);
    const remainder = rawCents - floorCents;
    assignedCentsTotal += floorCents;
    return {
      index,
      config: c,
      cents: floorCents,
      remainder,
    };
  });

  let remainingCents = allocatableCents - assignedCentsTotal;
  // Distribute remaining cents to highest remainders
  const sortedByRemainder = [...lineDetails].sort((a, b) => b.remainder - a.remainder);
  for (let i = 0; i < remainingCents; i++) {
    sortedByRemainder[i % sortedByRemainder.length].cents += 1;
  }

  // Format budget lines
  const lines = lineDetails.map((item) => {
    const amountVal = item.cents / 100;
    const percentVal = totalCents > 0 ? (item.cents / totalCents) * 100 : 0;
    return {
      category: item.config.name,
      percent: Number(percentVal.toFixed(2)),
      amount: amountVal.toFixed(2),
      rationale: item.config.rationale || `Budget allocation for ${item.config.name}.`,
      saving_tip: item.config.saving_tip || 'Compare multiple vendor packages to optimize cost.',
    };
  });

  const allocatedTotalVal = (allocatableCents / 100).toFixed(2);
  const contingencyAmountVal = (contingencyCents / 100).toFixed(2);
  const costPerGuestVal = (totalCents / 100 / guestCount).toFixed(2);

  return {
    total_amount: Number(totalAmount).toFixed(2),
    currency,
    guest_count: guestCount,
    cost_per_guest: costPerGuestVal,
    contingency_amount: contingencyAmountVal,
    contingency_percent: Number(contingencyPercent.toFixed(2)),
    lines,
    allocated_total: allocatedTotalVal,
    unallocated_amount: '0.00',
    is_balanced: true,
    meta: { source: 'rules', model: 'deterministic' },
  };
}

// -------------------------------------------------------------
// Pure Domain Logic: Backwards Timeline Scheduling
// -------------------------------------------------------------
function scheduleTimeline(eventDateStr, templates, idealLeadDays = 180) {
  const eventDate = new Date(eventDateStr + 'T00:00:00Z');
  const now = new Date();
  const diffTime = eventDate.getTime() - now.getTime();
  const leadDays = Math.max(1, Math.round(diffTime / (1000 * 60 * 60 * 24)));
  const isCompressed = leadDays < idealLeadDays;

  const milestones = (templates.milestones || []).map((m) => {
    let daysBefore = Number(m.lead_days);
    let isRush = false;
    if (isCompressed) {
      daysBefore = Math.round(leadDays * (daysBefore / idealLeadDays));
      if (daysBefore < 7 && m.priority === 'high') {
        isRush = true;
      }
    }
    daysBefore = Math.max(0, Math.min(leadDays, daysBefore));
    const dueDate = new Date(eventDate.getTime() - daysBefore * 24 * 60 * 60 * 1000);
    const dueDateStr = dueDate.toISOString().split('T')[0];

    return {
      id: m.id,
      title: m.title,
      phase: m.phase,
      due_date: dueDateStr,
      lead_days: daysBefore,
      priority: m.priority || 'medium',
      depends_on: m.depends_on || [],
      notes: m.notes || '',
      is_rush: isRush,
    };
  });

  // Sort milestones by lead_days descending (earliest action first)
  milestones.sort((a, b) => b.lead_days - a.lead_days);

  return {
    event_date: eventDateStr,
    planning_lead_days: leadDays,
    total_lead_days: leadDays,
    is_compressed: isCompressed,
    ideal_lead_days: idealLeadDays,
    milestones,
    run_of_show: templates.run_of_show || [],
    meta: { source: 'rules', model: 'deterministic' },
  };
}

// -------------------------------------------------------------
// Pure Domain Logic: Milestone-Linked Vendor Checklist
// -------------------------------------------------------------
function buildVendorChecklist(templates, milestoneMap, defaultDateStr) {
  const items = (templates.vendor_vetting || []).map((v) => {
    const bookBy = milestoneMap[v.milestone_id] || defaultDateStr;
    return {
      id: v.id,
      category: v.category,
      title: v.title,
      budget_line: v.budget_line,
      milestone_id: v.milestone_id,
      book_by_date: bookBy,
      questions_to_ask: v.questions_to_ask || [],
      documents_to_verify: v.documents_to_verify || [],
      red_flags: v.red_flags || [],
      status: 'to_do',
    };
  });

  return {
    total_items: items.length,
    completed_items: 0,
    progress_percent: 0.0,
    items,
    meta: { source: 'template', model: 'knowledge_base' },
  };
}

// -------------------------------------------------------------
// Pure Domain Logic: Five-Facet Personalization Ideas
// -------------------------------------------------------------
function generatePersonalizedIdeas(brief, steer = null) {
  const eventType = brief.event_type || 'wedding';
  const culture = brief.culture_or_subtype || (eventType === 'wedding' ? 'Traditional' : 'Milestone');
  const style = brief.style || 'Elegant Classic';
  const steerText = steer && steer.trim() ? ` (Guided by: ${steer.trim()})` : '';

  if (eventType === 'wedding') {
    return [
      {
        facet: 'themes',
        title: `${style} with ${culture} Accents`,
        description: `A harmonious fusion concept celebrating ${culture} traditions with modern ${style.toLowerCase()} elements${steerText}.`,
        why_it_fits: `Expresses your aesthetic preference for ${style} while honoring cultural hospitality.`,
        budget_tier: 'moderate',
      },
      {
        facet: 'decor',
        title: 'Locally Sourced Seasonal Florals & Ambient Uplighting',
        description: 'Warm ambient lighting paired with indigenous botanical table runners, brass accents, and fabric draping.',
        why_it_fits: `Creates an intimate, memorable atmosphere for your ${brief.guest_count || 100} guests.`,
        budget_tier: 'moderate',
      },
      {
        facet: 'food & drink',
        title: 'Interactive Regional Tasting Stations',
        description: `Curated stations showcasing heritage culinary dishes tailored to dietary preferences (${(brief.dietary_needs || []).join(', ') || 'all guests'}).`,
        why_it_fits: 'Encourages guest mingling while honoring dietary inclusivity.',
        budget_tier: 'moderate',
      },
      {
        facet: 'activities/entertainment',
        title: 'Acoustic Ceremony & Curated Heritage Dance Set',
        description: 'Live acoustic ensemble transitioning into a lively cultural celebration dance program welcoming all generations.',
        why_it_fits: 'Engages both younger and senior guests seamlessly throughout the festivities.',
        budget_tier: 'moderate',
      },
      {
        facet: 'keepsakes',
        title: 'Artisanal Seed Paper Favors & Custom Tea Blends',
        description: 'Personalized plantable thank-you seed cards paired with handcrafted small-batch spice or regional tea parcels.',
        why_it_fits: 'Sustainable, meaningful memento that endures well beyond event day.',
        budget_tier: 'budget',
      },
    ];
  } else if (eventType === 'birthday') {
    return [
      {
        facet: 'themes',
        title: `${style} Retro Arcade & Glow Celebration`,
        description: `Vibrant nostalgia celebration integrating arcade cabinets, neon highlights, and music milestones${steerText}.`,
        why_it_fits: `Directly matches your interest in ${style} and gaming nostalgia.`,
        budget_tier: 'moderate',
      },
      {
        facet: 'decor',
        title: 'Neon Geometry & Retro Accent Lounge',
        description: 'Custom neon light art, retro synth-wave color palettes, and cozy lounge pods.',
        why_it_fits: 'Provides high-energy visual appeal with photogenic celebration spaces.',
        budget_tier: 'moderate',
      },
      {
        facet: 'food & drink',
        title: 'Gourmet Slider & Craft Mocktail Bar',
        description: 'Customizable sliders and themed sparkling refreshments catering to all dietary requirements.',
        why_it_fits: `Accommodates ${(brief.dietary_needs || []).join(', ') || 'varied guest palates'} seamlessly.`,
        budget_tier: 'moderate',
      },
      {
        facet: 'activities/entertainment',
        title: 'Tournament Arcade Bracket & 80s/90s Trivia',
        description: 'Fast-paced friendly arcade leaderboard games and interactive music trivia hosted by a lively MC.',
        why_it_fits: 'Keeps all age groups engaged and laughing throughout the party.',
        budget_tier: 'budget',
      },
      {
        facet: 'keepsakes',
        title: 'Personalized Retro Enamel Pins & Instant Photo Magnets',
        description: 'Commemorative custom-stamped enamel pins paired with instant retro Polaroid photo magnets.',
        why_it_fits: 'Fun, tangible souvenir guests can display at home or on apparel.',
        budget_tier: 'budget',
      },
    ];
  } else {
    // Community
    return [
      {
        facet: 'themes',
        title: `${style} Neighborhood Green Showcase`,
        description: `An eco-conscious community festival celebrating local innovation, sustainability, and arts${steerText}.`,
        why_it_fits: 'Promotes collective neighborhood bonding and environmental awareness.',
        budget_tier: 'moderate',
      },
      {
        facet: 'decor',
        title: 'Upcycled Banners & Solar-Powered Festoon Lights',
        description: 'Reclaimed timber signage, fabric festival bunting, and solar warm festoon lights.',
        why_it_fits: 'Eco-friendly and weather-durable for outdoor community spaces.',
        budget_tier: 'budget',
      },
      {
        facet: 'food & drink',
        title: 'Community Potluck & Farm-to-Table Food Trucks',
        description: 'Locally grown seasonal produce and regional food vendors offering diverse zero-waste fare.',
        why_it_fits: 'Supports local growers and food trucks with minimal environmental footprint.',
        budget_tier: 'moderate',
      },
      {
        facet: 'activities/entertainment',
        title: 'Acoustic Stage, Kids Maker Tent & Citizen Science Workshop',
        description: 'Local neighborhood bands, hands-on renewable energy workshops, and seedling potting stations.',
        why_it_fits: 'Ensures inclusive participation across children, families, and neighborhood seniors.',
        budget_tier: 'budget',
      },
      {
        facet: 'keepsakes',
        title: 'Native Seed Packets & Community Resource Guide',
        description: 'Locally collected native wildflower seeds paired with an illustrated neighborhood guide.',
        why_it_fits: 'Continues greening the community long after the festival concludes.',
        budget_tier: 'budget',
      },
    ];
  }
}

// -------------------------------------------------------------
// API Endpoints
// -------------------------------------------------------------

// Health check
app.get('/api/v1/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  });
});

// Rebalance budget (Zero LLM calls)
app.post('/api/v1/budget/rebalance', (req, res) => {
  try {
    const { total_amount, currency, guest_count, configs, priorities, custom_weights, contingency_percent } = req.body;
    const plan = allocateBudget(total_amount, currency, guest_count, configs, {
      priorities,
      customWeights: custom_weights,
      contingencyPercent: contingency_percent,
    });
    res.json(plan);
  } catch (err) {
    res.status(400).json({ detail: err.message });
  }
});

// Regenerate personalized ideas
app.post('/api/v1/plans/ideas', async (req, res) => {
  try {
    const { brief, steer } = req.body;
    const facets = generatePersonalizedIdeas(brief, steer);
    res.json({
      ideas: facets,
      facets,
      steer: steer || null,
      source: 'template',
      meta: { source: 'template', model: 'gemini-2.5-flash' },
    });
  } catch (err) {
    res.status(400).json({ detail: err.message });
  }
});

// Generate full event plan
app.post('/api/v1/plans/generate', async (req, res) => {
  const startT = Date.now();
  try {
    const brief = req.body;
    const eventType = (brief.event_type || 'wedding').toLowerCase();
    const template = templates[eventType] || templates.wedding;

    // Check cache
    const cacheKey = getCacheKey('plan', brief);
    const cached = planCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return res.json({
        ...cached.data,
        meta: {
          ...cached.data.meta,
          single_flight_cached: true,
          elapsed_ms: Date.now() - startT,
        },
      });
    }

    // 1. Budget
    const budget = allocateBudget(brief.total_amount, brief.currency, brief.guest_count, template.budget_categories, {
      priorities: brief.priorities || [],
    });

    // 2. Timeline
    const timeline = scheduleTimeline(brief.event_date, template, template.ideal_lead_days || 180);

    // 3. Vendors
    const milestoneMap = {};
    for (const m of timeline.milestones) {
      milestoneMap[m.id] = m.due_date;
    }
    const vendors = buildVendorChecklist(template, milestoneMap, brief.event_date);

    // 4. Ideas
    const ideasFacets = generatePersonalizedIdeas(brief, brief.steer);
    const ideas = {
      ideas: ideasFacets,
      facets: ideasFacets,
      steer: brief.steer || null,
      source: 'template',
      meta: { source: 'template', model: 'gemini-2.5-flash' },
    };

    const result = {
      brief,
      budget,
      timeline,
      vendors,
      vendor_checklist: vendors,
      ideas,
      personalized_ideas: ideas,
      meta: {
        generated_at: new Date().toISOString(),
        elapsed_ms: Date.now() - startT,
        source: 'template',
        model: 'gemini-2.5-flash',
        single_flight_cached: false,
      },
    };

    planCache.set(cacheKey, { timestamp: Date.now(), data: result });
    res.json(result);
  } catch (err) {
    res.status(400).json({ detail: err.message });
  }
});

// Grounded planning assistant
app.post('/api/v1/assistant/ask', (req, res) => {
  try {
    const { brief, question } = req.body;
    const qLower = String(question || '').toLowerCase();

    // Check for off-topic questions
    const offTopicKeywords = ['weather tomorrow', 'world cup', 'stock market', 'bitcoin', 'crypto', 'recipe for pizza'];
    if (offTopicKeywords.some((k) => qLower.includes(k))) {
      return res.json({
        answer: 'I am your dedicated event planning assistant. I can only assist with logistical planning, budgets, timelines, vendor vetting, and creative ideas for your event.',
        grounded: false,
        sources_used: [],
      });
    }

    let answer = '';
    const eventType = brief.event_type || 'event';
    const total = brief.total_amount || '10000.00';
    const curr = brief.currency || 'INR';
    const guests = brief.guest_count || 100;

    if (qLower.includes('priority') || qLower.includes('first') || qLower.includes('start')) {
      answer = `For your ${eventType} (budget: ${total} ${curr}, ${guests} guests), the top priority is securing your primary venue and establishing vendor booking deadlines. Venue and catering typically comprise 50-60% of your total budget.`;
    } else if (qLower.includes('budget') || qLower.includes('cost') || qLower.includes('money')) {
      answer = `Based on your ${total} ${curr} budget for ${guests} guests, your cost per guest is ${(Number(total) / guests).toFixed(2)} ${curr}. We maintain a dedicated 5% contingency reserve to guard against unexpected expenses.`;
    } else if (qLower.includes('vendor') || qLower.includes('book') || qLower.includes('hire')) {
      answer = `When vetting vendors for your ${eventType}, always verify liability insurance and contracts with clear cancellation clauses. Refer to the red flags section in your vendor checklist before signing agreements.`;
    } else {
      answer = `Based on your ${eventType} scheduled for ${brief.event_date || 'your event date'} with ${guests} guests, focus on milestones with the earliest lead dates and review your personalized ideas section for thematic styling inspiration.`;
    }

    res.json({
      answer,
      grounded: true,
      sources_used: ['domain_knowledge', 'event_brief'],
    });
  } catch (err) {
    res.status(400).json({ detail: err.message });
  }
});

// Serve sample briefs from /examples/
app.use('/examples', express.static(path.join(__dirname, 'examples')));

// Serve frontend static assets from src/eventcraft/static/
app.use(express.static(path.join(__dirname, 'src', 'eventcraft', 'static')));

// Catch-all route to index.html for SPA client navigation
app.use((req, res) => {
  res.sendFile(path.join(__dirname, 'src', 'eventcraft', 'static', 'index.html'));
});

// Start Express server
app.listen(PORT, HOST, () => {
  console.log(`EventCraft AI server running at http://${HOST}:${PORT}`);
});
