export interface BlogContentBlock {
  type: 'paragraph' | 'heading' | 'list';
  text?: string;
  items?: string[];
}

export interface BlogPost {
  slug: string;
  title: string;
  summary: string;
  date: string;
  author: string;
  readingTime: string;
  body: BlogContentBlock[];
}

const posts: BlogPost[] = [
  {
    slug: 'crypto-ready-subscriptions-for-turf-crews',
    title: 'Crypto-ready subscriptions for turf crews',
    summary: 'Designing a low-friction onboarding flow that lets municipal grounds teams pay with BTC, ETH, or TON.',
    date: '2024-04-09',
    author: 'Sodmaster Intelligence',
    readingTime: '5 min read',
    body: [
      {
        type: 'paragraph',
        text: 'Grounds directors are under pressure to modernise payments without adding complexity to procurement workflows. Crypto subscriptions unlock instant settlement while keeping spend predictable.'
      },
      {
        type: 'heading',
        text: 'Why crypto-first billing matters'
      },
      {
        type: 'list',
        items: [
          'Treasury flexibility across USD, BTC, ETH, and TON balances.',
          'Programmable settlement for performance-based bonuses.',
          'Immutable audit trails that satisfy municipal oversight.'
        ]
      },
      {
        type: 'paragraph',
        text: 'Sodmaster pairs blockchain settlement with AI-led turf analytics so that budget holders get confidence alongside speed. Every invoice is enriched with moisture telemetry, crew dispatch logs, and predictive maintenance flags.'
      },
      {
        type: 'paragraph',
        text: 'Adopting crypto subscriptions is less about speculation and more about resilience. With automated tier upgrades and hedged treasury routing, CFOs finally align sustainability goals with financial stewardship.'
      }
    ]
  },
  {
    slug: 'designing-engaging-groundskeeping-tiers',
    title: 'Designing engaging groundskeeping tiers',
    summary: 'How to communicate value behind AI-augmented turf operations for facilities teams.',
    date: '2024-04-02',
    author: 'Sodmaster Intelligence',
    readingTime: '4 min read',
    body: [
      {
        type: 'paragraph',
        text: 'Subscription fatigue is real, but field teams still crave predictable service. The answer is intentional tier design that emphasises measurable outcomes and transparent automation.'
      },
      {
        type: 'heading',
        text: 'Three principles for compelling tiers'
      },
      {
        type: 'list',
        items: [
          'Lead with impact metrics such as water savings and crew response times.',
          'Bundle AI recommendations with human concierge expertise for reassurance.',
          'Spotlight sustainability credits that unlock when teams adopt smart irrigation.'
        ]
      },
      {
        type: 'paragraph',
        text: 'Our Growth and Enterprise plans surface ROI moments in real time: heat stress alerts trigger proactive roll-outs, while crypto loyalty keeps stakeholders invested in greener outcomes.'
      },
      {
        type: 'paragraph',
        text: 'When facility directors can preview the playbooks and automations aligned to each tier, purchase decisions shift from cost scrutiny to outcome acceleration.'
      }
    ]
  }
];

export default posts;
