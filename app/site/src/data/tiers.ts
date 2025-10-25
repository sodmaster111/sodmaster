export interface Tier {
  id: string;
  name: string;
  price: number;
  summary: string;
  perks: string[];
  highlight?: boolean;
}

const tiers: Tier[] = [
  {
    id: 'starter',
    name: 'Starter',
    price: 99,
    summary: 'Launch crypto-enabled turf subscriptions with curated playbooks.',
    perks: [
      'USD, BTC, ETH, TON invoicing',
      'Automated irrigation insights',
      'Monthly performance digest'
    ]
  },
  {
    id: 'growth',
    name: 'Growth',
    price: 249,
    summary: 'Unlock proactive AI scheduling and on-site crew coordination.',
    perks: [
      'Dynamic irrigation tuning',
      'Crew dispatch automations',
      'Ton-based loyalty rewards'
    ],
    highlight: true
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 549,
    summary: 'Scale complex grounds portfolios with dedicated success engineering.',
    perks: [
      'Portfolio health twin',
      'Bespoke compliance automations',
      '24/7 crypto treasury monitoring'
    ]
  }
];

export default tiers;
