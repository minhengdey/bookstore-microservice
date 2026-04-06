"""
build_kb.py
-----------
Builds the service knowledge base (KB).

Steps:
  1. Define (or load) service records
  2. Format each record into a rich text document
  3. Encode with Sentence-Transformers
  4. Persist raw KB to JSON for human inspection

Run:
    python build_kb.py
"""

import json
import os
import sys
from pathlib import Path

# Đảm bảo output path mặc định trỏ đến ai_engine/kb/
_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_KB_PATH = str(_THIS_DIR / "kb" / "knowledge_base.json")

# ──────────────────────────────────────────────
# 1. Service Catalogue
#    In production: load from a database or CSV.
# ──────────────────────────────────────────────

SERVICE_CATALOGUE = [
    {
        "service_id": "SVC001",
        "service_name": "Premium Health Insurance",
        "category": "Insurance",
        "description": "Comprehensive health coverage including inpatient, outpatient, dental, and vision benefits. Suitable for families and individuals who want zero-surprise medical bills.",
        "target_age_range": "25-60",
        "price_range": "$$",
        "tags": [
            "health",
            "medical",
            "insurance",
            "family",
            "coverage"
        ]
    },
    {
        "service_id": "SVC002",
        "service_name": "Smart Investment Portfolio",
        "category": "Finance",
        "description": "AI-driven investment management with diversified portfolios across stocks, bonds, ETFs, and crypto. Ideal for medium-to-long term wealth growth with personalised risk profiling.",
        "target_age_range": "25-55",
        "price_range": "$$$",
        "tags": [
            "investment",
            "finance",
            "wealth",
            "portfolio",
            "stocks"
        ]
    },
    {
        "service_id": "SVC003",
        "service_name": "E-Learning Pro Subscription",
        "category": "Education",
        "description": "Unlimited access to 10,000+ courses in technology, business, design, and personal development. Includes certificates, mentorship sessions, and a community of 2M+ learners.",
        "target_age_range": "18-45",
        "price_range": "$",
        "tags": [
            "education",
            "learning",
            "courses",
            "skills",
            "career"
        ]
    },
    {
        "service_id": "SVC004",
        "service_name": "Home Security System",
        "category": "Smart Home",
        "description": "24/7 monitored home security with AI motion detection, smart locks, and real-time mobile alerts. Easy DIY installation with professional monitoring option.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "security",
            "home",
            "smart",
            "safety",
            "IoT"
        ]
    },
    {
        "service_id": "SVC005",
        "service_name": "Telehealth Consultation",
        "category": "Healthcare",
        "description": "On-demand video consultations with licensed doctors and specialists. Prescriptions, lab referrals, and mental health support \u2014 all from the comfort of home.",
        "target_age_range": "18-70",
        "price_range": "$",
        "tags": [
            "telehealth",
            "doctor",
            "healthcare",
            "online",
            "mental health"
        ]
    },
    {
        "service_id": "SVC006",
        "service_name": "Premium Travel Insurance",
        "category": "Insurance",
        "description": "Worldwide travel coverage including trip cancellation, medical emergency, luggage loss, and flight delay compensation. Designed for frequent and leisure travellers.",
        "target_age_range": "20-65",
        "price_range": "$$",
        "tags": [
            "travel",
            "insurance",
            "trip",
            "holiday",
            "coverage"
        ]
    },
    {
        "service_id": "SVC007",
        "service_name": "Business Cloud Suite",
        "category": "Technology",
        "description": "All-in-one cloud platform for SMEs: CRM, project management, invoicing, HR, and analytics. Scales from 1 to 500 employees with enterprise-grade security.",
        "target_age_range": "25-55",
        "price_range": "$$$",
        "tags": [
            "business",
            "cloud",
            "SaaS",
            "CRM",
            "enterprise",
            "SME"
        ]
    },
    {
        "service_id": "SVC008",
        "service_name": "Fitness & Nutrition Coaching",
        "category": "Wellness",
        "description": "Personalised workout plans, macro tracking, and weekly 1-on-1 video coaching sessions with certified trainers. Suitable for weight loss, muscle gain, or general well-being goals.",
        "target_age_range": "18-55",
        "price_range": "$$",
        "tags": [
            "fitness",
            "nutrition",
            "workout",
            "wellness",
            "health",
            "coach"
        ]
    },
    {
        "service_id": "SVC009",
        "service_name": "Legal Advisory Membership",
        "category": "Legal",
        "description": "Unlimited consultations with qualified lawyers covering contracts, family law, property, and business law. Document review and draft services included for members.",
        "target_age_range": "25-65",
        "price_range": "$$$",
        "tags": [
            "legal",
            "lawyer",
            "contract",
            "advisory",
            "property",
            "business"
        ]
    },
    {
        "service_id": "SVC010",
        "service_name": "Children Education Fund",
        "category": "Finance",
        "description": "A government-linked savings plan optimised for children's education expenses. Tax-advantaged contributions, guaranteed growth, and flexible withdrawal for tuition fees.",
        "target_age_range": "25-45",
        "price_range": "$$",
        "tags": [
            "children",
            "education",
            "savings",
            "fund",
            "tuition",
            "family"
        ]
    },
    {
        "service_id": "SVC011",
        "service_name": "Cyber Security Shield",
        "category": "Technology",
        "description": "Enterprise-grade cyber protection for individuals and small businesses: VPN, dark web monitoring, identity theft protection, and real-time threat intelligence.",
        "target_age_range": "20-60",
        "price_range": "$$",
        "tags": [
            "cyber",
            "security",
            "VPN",
            "privacy",
            "identity",
            "protection"
        ]
    },
    {
        "service_id": "SVC012",
        "service_name": "Retirement Savings Plan",
        "category": "Finance",
        "description": "Long-term pension and retirement savings product with employer-matching options, low fees, and diversified fund choices. Designed to maximise post-retirement income.",
        "target_age_range": "30-60",
        "price_range": "$$",
        "tags": [
            "retirement",
            "pension",
            "savings",
            "long-term",
            "finance"
        ]
    },
    {
        "service_id": "SVC013",
        "service_name": "Pet Care & Insurance",
        "category": "Insurance",
        "description": "Vet bills, surgery, medication, and wellness check coverage for dogs, cats, and exotic pets. Includes 24/7 pet telehealth and an online vet pharmacy.",
        "target_age_range": "20-55",
        "price_range": "$",
        "tags": [
            "pet",
            "insurance",
            "vet",
            "animals",
            "dog",
            "cat"
        ]
    },
    {
        "service_id": "SVC014",
        "service_name": "Real Estate Advisory",
        "category": "Property",
        "description": "Expert guidance for buying, selling, and renting property. Includes mortgage pre-approval support, valuation reports, neighbourhood analytics, and legal due-diligence.",
        "target_age_range": "28-65",
        "price_range": "$$$",
        "tags": [
            "real estate",
            "property",
            "mortgage",
            "buying",
            "selling",
            "rent"
        ]
    },
    {
        "service_id": "SVC015",
        "service_name": "Digital Marketing Starter Pack",
        "category": "Business",
        "description": "Done-for-you digital marketing: SEO audit, social media strategy, Google Ads management, and monthly performance reporting. Tailored for startups and small businesses.",
        "target_age_range": "22-50",
        "price_range": "$$",
        "tags": [
            "marketing",
            "SEO",
            "social media",
            "ads",
            "business",
            "startup"
        ]
    },
    {
        "service_id": "SVC016",
        "service_name": "Ultimate Education Dashboard",
        "category": "Education",
        "description": "A state-of-the-art education dashboard offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "AI",
            "IoT",
            "business",
            "health",
            "tech"
        ]
    },
    {
        "service_id": "SVC017",
        "service_name": "Smart Retail Advisory",
        "category": "Retail",
        "description": "A state-of-the-art retail advisory offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$",
        "tags": [
            "AI",
            "cloud",
            "business",
            "tech",
            "education"
        ]
    },
    {
        "service_id": "SVC018",
        "service_name": "Premium Entertainment Package",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment package offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$",
        "tags": [
            "AI",
            "analytics",
            "health",
            "SaaS"
        ]
    },
    {
        "service_id": "SVC019",
        "service_name": "Pro Education Dashboard",
        "category": "Education",
        "description": "A state-of-the-art education dashboard offering pro features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$$",
        "tags": [
            "IoT",
            "health",
            "security",
            "marketing",
            "AI"
        ]
    },
    {
        "service_id": "SVC020",
        "service_name": "Creative Retail Package",
        "category": "Retail",
        "description": "A state-of-the-art retail package offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$",
        "tags": [
            "design",
            "health",
            "analytics",
            "cloud"
        ]
    },
    {
        "service_id": "SVC021",
        "service_name": "Creative Finance Dashboard",
        "category": "Finance",
        "description": "A state-of-the-art finance dashboard offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$",
        "tags": [
            "health",
            "IoT",
            "design"
        ]
    },
    {
        "service_id": "SVC022",
        "service_name": "Enterprise Property Solutions",
        "category": "Property",
        "description": "A state-of-the-art property solutions offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$",
        "tags": [
            "design",
            "security",
            "education",
            "IoT",
            "business"
        ]
    },
    {
        "service_id": "SVC023",
        "service_name": "Enterprise Education Platform",
        "category": "Education",
        "description": "A state-of-the-art education platform offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$",
        "tags": [
            "cloud",
            "tech",
            "health"
        ]
    },
    {
        "service_id": "SVC024",
        "service_name": "Personal Fitness Coaching",
        "category": "Fitness",
        "description": "A state-of-the-art fitness coaching offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$$",
        "tags": [
            "creative",
            "auto",
            "marketing",
            "data",
            "finance"
        ]
    },
    {
        "service_id": "SVC025",
        "service_name": "Creative Software Coaching",
        "category": "Software",
        "description": "A state-of-the-art software coaching offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "AI",
            "design",
            "marketing",
            "education"
        ]
    },
    {
        "service_id": "SVC026",
        "service_name": "Ultimate Health Network",
        "category": "Health",
        "description": "A state-of-the-art health network offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "creative",
            "health",
            "data"
        ]
    },
    {
        "service_id": "SVC027",
        "service_name": "Automated Technology Dashboard",
        "category": "Technology",
        "description": "A state-of-the-art technology dashboard offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$",
        "tags": [
            "marketing",
            "IoT",
            "education",
            "analytics"
        ]
    },
    {
        "service_id": "SVC028",
        "service_name": "Personal Automotive System",
        "category": "Automotive",
        "description": "A state-of-the-art automotive system offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$",
        "tags": [
            "IoT",
            "SaaS",
            "auto"
        ]
    },
    {
        "service_id": "SVC029",
        "service_name": "Ultimate Automotive Solutions",
        "category": "Automotive",
        "description": "A state-of-the-art automotive solutions offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$",
        "tags": [
            "marketing",
            "design",
            "tech"
        ]
    },
    {
        "service_id": "SVC030",
        "service_name": "Creative Software Hub",
        "category": "Software",
        "description": "A state-of-the-art software hub offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "finance",
            "design",
            "data"
        ]
    },
    {
        "service_id": "SVC031",
        "service_name": "Personal Retail Solutions",
        "category": "Retail",
        "description": "A state-of-the-art retail solutions offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$$",
        "tags": [
            "health",
            "auto",
            "business"
        ]
    },
    {
        "service_id": "SVC032",
        "service_name": "Pro Health Coaching",
        "category": "Health",
        "description": "A state-of-the-art health coaching offering pro features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$",
        "tags": [
            "marketing",
            "cloud",
            "IoT",
            "education",
            "AI"
        ]
    },
    {
        "service_id": "SVC033",
        "service_name": "Cloud Education Hub",
        "category": "Education",
        "description": "A state-of-the-art education hub offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$",
        "tags": [
            "education",
            "tech",
            "data",
            "creative"
        ]
    },
    {
        "service_id": "SVC034",
        "service_name": "Premium Health Coaching",
        "category": "Health",
        "description": "A state-of-the-art health coaching offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$",
        "tags": [
            "business",
            "auto",
            "finance"
        ]
    },
    {
        "service_id": "SVC035",
        "service_name": "Ultimate Health System",
        "category": "Health",
        "description": "A state-of-the-art health system offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "auto",
            "IoT",
            "home"
        ]
    },
    {
        "service_id": "SVC036",
        "service_name": "Cloud Automotive Coaching",
        "category": "Automotive",
        "description": "A state-of-the-art automotive coaching offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "education",
            "SaaS",
            "analytics",
            "marketing",
            "home"
        ]
    },
    {
        "service_id": "SVC037",
        "service_name": "Pro Finance Network",
        "category": "Finance",
        "description": "A state-of-the-art finance network offering pro features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$$",
        "tags": [
            "education",
            "finance",
            "AI",
            "analytics",
            "SaaS"
        ]
    },
    {
        "service_id": "SVC038",
        "service_name": "Basic Legal Platform",
        "category": "Legal",
        "description": "A state-of-the-art legal platform offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$",
        "tags": [
            "data",
            "education",
            "design",
            "IoT"
        ]
    },
    {
        "service_id": "SVC039",
        "service_name": "Digital Entertainment Package",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment package offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$$",
        "tags": [
            "security",
            "finance",
            "marketing"
        ]
    },
    {
        "service_id": "SVC040",
        "service_name": "Ultimate Retail Suite",
        "category": "Retail",
        "description": "A state-of-the-art retail suite offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$",
        "tags": [
            "analytics",
            "business",
            "SaaS",
            "data"
        ]
    },
    {
        "service_id": "SVC041",
        "service_name": "Creative Entertainment Platform",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment platform offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$$",
        "tags": [
            "design",
            "AI",
            "IoT",
            "cloud"
        ]
    },
    {
        "service_id": "SVC042",
        "service_name": "Smart Fitness Suite",
        "category": "Fitness",
        "description": "A state-of-the-art fitness suite offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$",
        "tags": [
            "cloud",
            "home",
            "design",
            "business",
            "education"
        ]
    },
    {
        "service_id": "SVC043",
        "service_name": "Smart Entertainment Solutions",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment solutions offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$$",
        "tags": [
            "IoT",
            "creative",
            "SaaS",
            "security",
            "marketing"
        ]
    },
    {
        "service_id": "SVC044",
        "service_name": "Premium Retail Hub",
        "category": "Retail",
        "description": "A state-of-the-art retail hub offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$",
        "tags": [
            "IoT",
            "home",
            "cloud"
        ]
    },
    {
        "service_id": "SVC045",
        "service_name": "Basic Retail Toolkit",
        "category": "Retail",
        "description": "A state-of-the-art retail toolkit offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "data",
            "business",
            "IoT"
        ]
    },
    {
        "service_id": "SVC046",
        "service_name": "Automated Finance Platform",
        "category": "Finance",
        "description": "A state-of-the-art finance platform offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "creative",
            "security",
            "education"
        ]
    },
    {
        "service_id": "SVC047",
        "service_name": "Cloud Retail Platform",
        "category": "Retail",
        "description": "A state-of-the-art retail platform offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$",
        "tags": [
            "cloud",
            "SaaS",
            "IoT",
            "creative",
            "design"
        ]
    },
    {
        "service_id": "SVC048",
        "service_name": "Personal Education Advisory",
        "category": "Education",
        "description": "A state-of-the-art education advisory offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$$",
        "tags": [
            "SaaS",
            "analytics",
            "auto"
        ]
    },
    {
        "service_id": "SVC049",
        "service_name": "Creative Legal Dashboard",
        "category": "Legal",
        "description": "A state-of-the-art legal dashboard offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$",
        "tags": [
            "analytics",
            "home",
            "finance",
            "data"
        ]
    },
    {
        "service_id": "SVC050",
        "service_name": "Cloud Legal Hub",
        "category": "Legal",
        "description": "A state-of-the-art legal hub offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "SaaS",
            "finance",
            "IoT"
        ]
    },
    {
        "service_id": "SVC051",
        "service_name": "Creative Smart Home Solutions",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home solutions offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$",
        "tags": [
            "marketing",
            "IoT",
            "analytics"
        ]
    },
    {
        "service_id": "SVC052",
        "service_name": "Cloud Property Advisory",
        "category": "Property",
        "description": "A state-of-the-art property advisory offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$",
        "tags": [
            "home",
            "finance",
            "IoT"
        ]
    },
    {
        "service_id": "SVC053",
        "service_name": "Premium Consulting Dashboard",
        "category": "Consulting",
        "description": "A state-of-the-art consulting dashboard offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$$",
        "tags": [
            "finance",
            "education",
            "home",
            "tech",
            "health"
        ]
    },
    {
        "service_id": "SVC054",
        "service_name": "Enterprise Entertainment Coaching",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment coaching offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "design",
            "data",
            "finance",
            "security"
        ]
    },
    {
        "service_id": "SVC055",
        "service_name": "Cloud Consulting Package",
        "category": "Consulting",
        "description": "A state-of-the-art consulting package offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$",
        "tags": [
            "home",
            "business",
            "AI",
            "marketing"
        ]
    },
    {
        "service_id": "SVC056",
        "service_name": "Pro Fitness Advisory",
        "category": "Fitness",
        "description": "A state-of-the-art fitness advisory offering pro features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "finance",
            "SaaS",
            "IoT"
        ]
    },
    {
        "service_id": "SVC057",
        "service_name": "Personal Legal System",
        "category": "Legal",
        "description": "A state-of-the-art legal system offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$$",
        "tags": [
            "finance",
            "tech",
            "marketing",
            "security"
        ]
    },
    {
        "service_id": "SVC058",
        "service_name": "Premium Automotive Toolkit",
        "category": "Automotive",
        "description": "A state-of-the-art automotive toolkit offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "data",
            "cloud",
            "finance"
        ]
    },
    {
        "service_id": "SVC059",
        "service_name": "Enterprise Entertainment Package",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment package offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$",
        "tags": [
            "creative",
            "education",
            "cloud",
            "auto"
        ]
    },
    {
        "service_id": "SVC060",
        "service_name": "Enterprise Smart Home Network",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home network offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "security",
            "SaaS",
            "education"
        ]
    },
    {
        "service_id": "SVC061",
        "service_name": "Advanced Technology Platform",
        "category": "Technology",
        "description": "A state-of-the-art technology platform offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "business",
            "AI",
            "creative",
            "analytics",
            "education"
        ]
    },
    {
        "service_id": "SVC062",
        "service_name": "Creative Property Service",
        "category": "Property",
        "description": "A state-of-the-art property service offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$$",
        "tags": [
            "data",
            "cloud",
            "AI",
            "SaaS",
            "IoT"
        ]
    },
    {
        "service_id": "SVC063",
        "service_name": "Advanced Education Coaching",
        "category": "Education",
        "description": "A state-of-the-art education coaching offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$$",
        "tags": [
            "SaaS",
            "AI",
            "education"
        ]
    },
    {
        "service_id": "SVC064",
        "service_name": "Premium Consulting Solutions",
        "category": "Consulting",
        "description": "A state-of-the-art consulting solutions offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$",
        "tags": [
            "health",
            "auto",
            "data",
            "AI",
            "finance"
        ]
    },
    {
        "service_id": "SVC065",
        "service_name": "Advanced Entertainment System",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment system offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$",
        "tags": [
            "cloud",
            "SaaS",
            "business"
        ]
    },
    {
        "service_id": "SVC066",
        "service_name": "Automated Fitness Toolkit",
        "category": "Fitness",
        "description": "A state-of-the-art fitness toolkit offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$",
        "tags": [
            "home",
            "security",
            "business",
            "design",
            "marketing"
        ]
    },
    {
        "service_id": "SVC067",
        "service_name": "Personal Education Service",
        "category": "Education",
        "description": "A state-of-the-art education service offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$",
        "tags": [
            "analytics",
            "health",
            "tech"
        ]
    },
    {
        "service_id": "SVC068",
        "service_name": "Cloud Software Package",
        "category": "Software",
        "description": "A state-of-the-art software package offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$$",
        "tags": [
            "finance",
            "data",
            "marketing",
            "cloud"
        ]
    },
    {
        "service_id": "SVC069",
        "service_name": "Advanced Education Hub",
        "category": "Education",
        "description": "A state-of-the-art education hub offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$",
        "tags": [
            "business",
            "finance",
            "health"
        ]
    },
    {
        "service_id": "SVC070",
        "service_name": "Digital Legal Membership",
        "category": "Legal",
        "description": "A state-of-the-art legal membership offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$",
        "tags": [
            "education",
            "design",
            "auto"
        ]
    },
    {
        "service_id": "SVC071",
        "service_name": "Automated Legal Coaching",
        "category": "Legal",
        "description": "A state-of-the-art legal coaching offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$$",
        "tags": [
            "data",
            "auto",
            "analytics",
            "IoT",
            "creative"
        ]
    },
    {
        "service_id": "SVC072",
        "service_name": "Personal Legal Coaching",
        "category": "Legal",
        "description": "A state-of-the-art legal coaching offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$",
        "tags": [
            "AI",
            "auto",
            "education",
            "health"
        ]
    },
    {
        "service_id": "SVC073",
        "service_name": "Ultimate Software Coaching",
        "category": "Software",
        "description": "A state-of-the-art software coaching offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$",
        "tags": [
            "creative",
            "design",
            "IoT"
        ]
    },
    {
        "service_id": "SVC074",
        "service_name": "Premium Legal Service",
        "category": "Legal",
        "description": "A state-of-the-art legal service offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "SaaS",
            "IoT",
            "security",
            "business"
        ]
    },
    {
        "service_id": "SVC075",
        "service_name": "Creative Finance Package",
        "category": "Finance",
        "description": "A state-of-the-art finance package offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$$",
        "tags": [
            "AI",
            "marketing",
            "creative",
            "security"
        ]
    },
    {
        "service_id": "SVC076",
        "service_name": "Premium Education Dashboard",
        "category": "Education",
        "description": "A state-of-the-art education dashboard offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$$",
        "tags": [
            "creative",
            "IoT",
            "security",
            "auto"
        ]
    },
    {
        "service_id": "SVC077",
        "service_name": "Basic Property Hub",
        "category": "Property",
        "description": "A state-of-the-art property hub offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$",
        "tags": [
            "IoT",
            "marketing",
            "security",
            "cloud"
        ]
    },
    {
        "service_id": "SVC078",
        "service_name": "Cloud Entertainment Dashboard",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment dashboard offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$",
        "tags": [
            "marketing",
            "health",
            "data"
        ]
    },
    {
        "service_id": "SVC079",
        "service_name": "Personal Finance Advisory",
        "category": "Finance",
        "description": "A state-of-the-art finance advisory offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "IoT",
            "education",
            "auto",
            "business"
        ]
    },
    {
        "service_id": "SVC080",
        "service_name": "Enterprise Technology Dashboard",
        "category": "Technology",
        "description": "A state-of-the-art technology dashboard offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$",
        "tags": [
            "AI",
            "education",
            "marketing",
            "cloud",
            "creative"
        ]
    },
    {
        "service_id": "SVC081",
        "service_name": "Ultimate Education Platform",
        "category": "Education",
        "description": "A state-of-the-art education platform offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$",
        "tags": [
            "education",
            "home",
            "data",
            "marketing"
        ]
    },
    {
        "service_id": "SVC082",
        "service_name": "Digital Retail Hub",
        "category": "Retail",
        "description": "A state-of-the-art retail hub offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$",
        "tags": [
            "education",
            "home",
            "data",
            "cloud",
            "finance"
        ]
    },
    {
        "service_id": "SVC083",
        "service_name": "Digital Education Dashboard",
        "category": "Education",
        "description": "A state-of-the-art education dashboard offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$$",
        "tags": [
            "marketing",
            "security",
            "health",
            "tech",
            "home"
        ]
    },
    {
        "service_id": "SVC084",
        "service_name": "Pro Technology Membership",
        "category": "Technology",
        "description": "A state-of-the-art technology membership offering pro features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$",
        "tags": [
            "IoT",
            "finance",
            "cloud"
        ]
    },
    {
        "service_id": "SVC085",
        "service_name": "Smart Consulting Service",
        "category": "Consulting",
        "description": "A state-of-the-art consulting service offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$",
        "tags": [
            "business",
            "auto",
            "design"
        ]
    },
    {
        "service_id": "SVC086",
        "service_name": "Ultimate Technology Membership",
        "category": "Technology",
        "description": "A state-of-the-art technology membership offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$",
        "tags": [
            "analytics",
            "security",
            "design",
            "AI",
            "IoT"
        ]
    },
    {
        "service_id": "SVC087",
        "service_name": "Cloud Fitness Package",
        "category": "Fitness",
        "description": "A state-of-the-art fitness package offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$$",
        "tags": [
            "home",
            "data",
            "marketing"
        ]
    },
    {
        "service_id": "SVC088",
        "service_name": "Personal Property Coaching",
        "category": "Property",
        "description": "A state-of-the-art property coaching offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$$",
        "tags": [
            "IoT",
            "AI",
            "design",
            "data"
        ]
    },
    {
        "service_id": "SVC089",
        "service_name": "Enterprise Health Membership",
        "category": "Health",
        "description": "A state-of-the-art health membership offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "security",
            "creative",
            "cloud",
            "marketing",
            "data"
        ]
    },
    {
        "service_id": "SVC090",
        "service_name": "Ultimate Education System",
        "category": "Education",
        "description": "A state-of-the-art education system offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$",
        "tags": [
            "marketing",
            "design",
            "analytics",
            "home"
        ]
    },
    {
        "service_id": "SVC091",
        "service_name": "Automated Education Package",
        "category": "Education",
        "description": "A state-of-the-art education package offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$",
        "tags": [
            "creative",
            "education",
            "business",
            "SaaS",
            "design"
        ]
    },
    {
        "service_id": "SVC092",
        "service_name": "Basic Health Service",
        "category": "Health",
        "description": "A state-of-the-art health service offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$",
        "tags": [
            "health",
            "tech",
            "home",
            "education",
            "auto"
        ]
    },
    {
        "service_id": "SVC093",
        "service_name": "Advanced Technology Advisory",
        "category": "Technology",
        "description": "A state-of-the-art technology advisory offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$",
        "tags": [
            "finance",
            "tech",
            "marketing",
            "creative"
        ]
    },
    {
        "service_id": "SVC094",
        "service_name": "Cloud Software Coaching",
        "category": "Software",
        "description": "A state-of-the-art software coaching offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$",
        "tags": [
            "analytics",
            "business",
            "health"
        ]
    },
    {
        "service_id": "SVC095",
        "service_name": "Automated Smart Home Dashboard",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home dashboard offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$",
        "tags": [
            "IoT",
            "creative",
            "data",
            "home",
            "auto"
        ]
    },
    {
        "service_id": "SVC096",
        "service_name": "Pro Health Platform",
        "category": "Health",
        "description": "A state-of-the-art health platform offering pro features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$$",
        "tags": [
            "auto",
            "data",
            "finance",
            "marketing"
        ]
    },
    {
        "service_id": "SVC097",
        "service_name": "Pro Smart Home Dashboard",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home dashboard offering pro features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$",
        "tags": [
            "finance",
            "marketing",
            "design"
        ]
    },
    {
        "service_id": "SVC098",
        "service_name": "Premium Automotive Advisory",
        "category": "Automotive",
        "description": "A state-of-the-art automotive advisory offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "education",
            "tech",
            "SaaS",
            "cloud"
        ]
    },
    {
        "service_id": "SVC099",
        "service_name": "Ultimate Entertainment Platform",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment platform offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$$",
        "tags": [
            "education",
            "IoT",
            "home",
            "business"
        ]
    },
    {
        "service_id": "SVC100",
        "service_name": "Automated Property Toolkit",
        "category": "Property",
        "description": "A state-of-the-art property toolkit offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$",
        "tags": [
            "analytics",
            "tech",
            "SaaS",
            "home",
            "finance"
        ]
    },
    {
        "service_id": "SVC101",
        "service_name": "Smart Property Package",
        "category": "Property",
        "description": "A state-of-the-art property package offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "creative",
            "marketing",
            "finance"
        ]
    },
    {
        "service_id": "SVC102",
        "service_name": "Automated Retail Package",
        "category": "Retail",
        "description": "A state-of-the-art retail package offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$",
        "tags": [
            "tech",
            "design",
            "business",
            "IoT"
        ]
    },
    {
        "service_id": "SVC103",
        "service_name": "Creative Fitness Suite",
        "category": "Fitness",
        "description": "A state-of-the-art fitness suite offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$",
        "tags": [
            "data",
            "finance",
            "auto",
            "creative"
        ]
    },
    {
        "service_id": "SVC104",
        "service_name": "Premium Property Membership",
        "category": "Property",
        "description": "A state-of-the-art property membership offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "data",
            "education",
            "home",
            "SaaS",
            "cloud"
        ]
    },
    {
        "service_id": "SVC105",
        "service_name": "Ultimate Legal Toolkit",
        "category": "Legal",
        "description": "A state-of-the-art legal toolkit offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$",
        "tags": [
            "tech",
            "auto",
            "finance",
            "design"
        ]
    },
    {
        "service_id": "SVC106",
        "service_name": "Digital Health Suite",
        "category": "Health",
        "description": "A state-of-the-art health suite offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$",
        "tags": [
            "analytics",
            "cloud",
            "design"
        ]
    },
    {
        "service_id": "SVC107",
        "service_name": "Advanced Retail Dashboard",
        "category": "Retail",
        "description": "A state-of-the-art retail dashboard offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$$",
        "tags": [
            "analytics",
            "finance",
            "security",
            "health"
        ]
    },
    {
        "service_id": "SVC108",
        "service_name": "Advanced Entertainment Suite",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment suite offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$",
        "tags": [
            "SaaS",
            "home",
            "auto"
        ]
    },
    {
        "service_id": "SVC109",
        "service_name": "Advanced Education System",
        "category": "Education",
        "description": "A state-of-the-art education system offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$",
        "tags": [
            "tech",
            "AI",
            "cloud"
        ]
    },
    {
        "service_id": "SVC110",
        "service_name": "Pro Smart Home Package",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home package offering pro features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$",
        "tags": [
            "AI",
            "auto",
            "tech",
            "finance",
            "home"
        ]
    },
    {
        "service_id": "SVC111",
        "service_name": "Basic Education Solutions",
        "category": "Education",
        "description": "A state-of-the-art education solutions offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$",
        "tags": [
            "SaaS",
            "analytics",
            "marketing",
            "tech"
        ]
    },
    {
        "service_id": "SVC112",
        "service_name": "Enterprise Property Suite",
        "category": "Property",
        "description": "A state-of-the-art property suite offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$$",
        "tags": [
            "health",
            "tech",
            "education",
            "finance",
            "security"
        ]
    },
    {
        "service_id": "SVC113",
        "service_name": "Basic Smart Home Service",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home service offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$",
        "tags": [
            "tech",
            "security",
            "creative",
            "auto"
        ]
    },
    {
        "service_id": "SVC114",
        "service_name": "Advanced Entertainment Package",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment package offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "creative",
            "finance",
            "auto",
            "AI"
        ]
    },
    {
        "service_id": "SVC115",
        "service_name": "Personal Retail Platform",
        "category": "Retail",
        "description": "A state-of-the-art retail platform offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$",
        "tags": [
            "tech",
            "health",
            "security",
            "analytics"
        ]
    },
    {
        "service_id": "SVC116",
        "service_name": "Creative Finance Platform",
        "category": "Finance",
        "description": "A state-of-the-art finance platform offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$",
        "tags": [
            "data",
            "SaaS",
            "AI",
            "analytics",
            "IoT"
        ]
    },
    {
        "service_id": "SVC117",
        "service_name": "Advanced Retail Solutions",
        "category": "Retail",
        "description": "A state-of-the-art retail solutions offering advanced features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$",
        "tags": [
            "security",
            "design",
            "tech",
            "education",
            "SaaS"
        ]
    },
    {
        "service_id": "SVC118",
        "service_name": "Digital Software Toolkit",
        "category": "Software",
        "description": "A state-of-the-art software toolkit offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "data",
            "health",
            "finance"
        ]
    },
    {
        "service_id": "SVC119",
        "service_name": "Cloud Automotive Service",
        "category": "Automotive",
        "description": "A state-of-the-art automotive service offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$",
        "tags": [
            "business",
            "finance",
            "home",
            "data",
            "creative"
        ]
    },
    {
        "service_id": "SVC120",
        "service_name": "Automated Finance Hub",
        "category": "Finance",
        "description": "A state-of-the-art finance hub offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$$",
        "tags": [
            "tech",
            "data",
            "health",
            "creative",
            "security"
        ]
    },
    {
        "service_id": "SVC121",
        "service_name": "Automated Property Solutions",
        "category": "Property",
        "description": "A state-of-the-art property solutions offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$",
        "tags": [
            "design",
            "AI",
            "creative",
            "finance",
            "analytics"
        ]
    },
    {
        "service_id": "SVC122",
        "service_name": "Digital Education Toolkit",
        "category": "Education",
        "description": "A state-of-the-art education toolkit offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "design",
            "marketing",
            "finance",
            "business"
        ]
    },
    {
        "service_id": "SVC123",
        "service_name": "Creative Property Network",
        "category": "Property",
        "description": "A state-of-the-art property network offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$",
        "tags": [
            "health",
            "SaaS",
            "design",
            "business",
            "AI"
        ]
    },
    {
        "service_id": "SVC124",
        "service_name": "Smart Automotive Solutions",
        "category": "Automotive",
        "description": "A state-of-the-art automotive solutions offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$",
        "tags": [
            "security",
            "IoT",
            "marketing",
            "home"
        ]
    },
    {
        "service_id": "SVC125",
        "service_name": "Basic Software Membership",
        "category": "Software",
        "description": "A state-of-the-art software membership offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$$",
        "tags": [
            "data",
            "tech",
            "education"
        ]
    },
    {
        "service_id": "SVC126",
        "service_name": "Automated Smart Home Network",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home network offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$$",
        "tags": [
            "business",
            "security",
            "marketing"
        ]
    },
    {
        "service_id": "SVC127",
        "service_name": "Digital Entertainment Service",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment service offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$$",
        "tags": [
            "home",
            "SaaS",
            "cloud",
            "IoT",
            "AI"
        ]
    },
    {
        "service_id": "SVC128",
        "service_name": "Ultimate Consulting Toolkit",
        "category": "Consulting",
        "description": "A state-of-the-art consulting toolkit offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$",
        "tags": [
            "AI",
            "cloud",
            "finance"
        ]
    },
    {
        "service_id": "SVC129",
        "service_name": "Smart Software Toolkit",
        "category": "Software",
        "description": "A state-of-the-art software toolkit offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$",
        "tags": [
            "IoT",
            "education",
            "data",
            "business"
        ]
    },
    {
        "service_id": "SVC130",
        "service_name": "Basic Property Network",
        "category": "Property",
        "description": "A state-of-the-art property network offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$",
        "tags": [
            "data",
            "cloud",
            "home",
            "security"
        ]
    },
    {
        "service_id": "SVC131",
        "service_name": "Creative Software Service",
        "category": "Software",
        "description": "A state-of-the-art software service offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$$",
        "tags": [
            "education",
            "tech",
            "business"
        ]
    },
    {
        "service_id": "SVC132",
        "service_name": "Smart Automotive Solutions",
        "category": "Automotive",
        "description": "A state-of-the-art automotive solutions offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$",
        "tags": [
            "design",
            "creative",
            "AI"
        ]
    },
    {
        "service_id": "SVC133",
        "service_name": "Premium Software Hub",
        "category": "Software",
        "description": "A state-of-the-art software hub offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "SaaS",
            "finance",
            "IoT"
        ]
    },
    {
        "service_id": "SVC134",
        "service_name": "Cloud Education Service",
        "category": "Education",
        "description": "A state-of-the-art education service offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$",
        "tags": [
            "auto",
            "IoT",
            "analytics",
            "business",
            "finance"
        ]
    },
    {
        "service_id": "SVC135",
        "service_name": "Premium Technology Toolkit",
        "category": "Technology",
        "description": "A state-of-the-art technology toolkit offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$",
        "tags": [
            "marketing",
            "finance",
            "AI",
            "SaaS"
        ]
    },
    {
        "service_id": "SVC136",
        "service_name": "Premium Legal Coaching",
        "category": "Legal",
        "description": "A state-of-the-art legal coaching offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "AI",
            "business",
            "data"
        ]
    },
    {
        "service_id": "SVC137",
        "service_name": "Basic Smart Home Advisory",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home advisory offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$$",
        "tags": [
            "design",
            "analytics",
            "education",
            "health"
        ]
    },
    {
        "service_id": "SVC138",
        "service_name": "Cloud Finance Toolkit",
        "category": "Finance",
        "description": "A state-of-the-art finance toolkit offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$",
        "tags": [
            "creative",
            "auto",
            "marketing",
            "health",
            "education"
        ]
    },
    {
        "service_id": "SVC139",
        "service_name": "Ultimate Finance Package",
        "category": "Finance",
        "description": "A state-of-the-art finance package offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$",
        "tags": [
            "creative",
            "education",
            "cloud"
        ]
    },
    {
        "service_id": "SVC140",
        "service_name": "Ultimate Smart Home Coaching",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home coaching offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$$",
        "tags": [
            "tech",
            "finance",
            "auto",
            "health"
        ]
    },
    {
        "service_id": "SVC141",
        "service_name": "Personal Legal Toolkit",
        "category": "Legal",
        "description": "A state-of-the-art legal toolkit offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$",
        "tags": [
            "business",
            "IoT",
            "creative"
        ]
    },
    {
        "service_id": "SVC142",
        "service_name": "Ultimate Fitness Network",
        "category": "Fitness",
        "description": "A state-of-the-art fitness network offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "home",
            "business",
            "security",
            "finance"
        ]
    },
    {
        "service_id": "SVC143",
        "service_name": "Cloud Legal Dashboard",
        "category": "Legal",
        "description": "A state-of-the-art legal dashboard offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$$",
        "tags": [
            "home",
            "marketing",
            "business"
        ]
    },
    {
        "service_id": "SVC144",
        "service_name": "Enterprise Software Package",
        "category": "Software",
        "description": "A state-of-the-art software package offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$",
        "tags": [
            "design",
            "data",
            "finance",
            "business"
        ]
    },
    {
        "service_id": "SVC145",
        "service_name": "Automated Automotive Package",
        "category": "Automotive",
        "description": "A state-of-the-art automotive package offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "30-65",
        "price_range": "$",
        "tags": [
            "business",
            "SaaS",
            "design",
            "health"
        ]
    },
    {
        "service_id": "SVC146",
        "service_name": "Digital Software Toolkit",
        "category": "Software",
        "description": "A state-of-the-art software toolkit offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "auto",
            "marketing",
            "health"
        ]
    },
    {
        "service_id": "SVC147",
        "service_name": "Creative Education System",
        "category": "Education",
        "description": "A state-of-the-art education system offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "design",
            "tech",
            "SaaS",
            "security"
        ]
    },
    {
        "service_id": "SVC148",
        "service_name": "Cloud Entertainment Network",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment network offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$$",
        "tags": [
            "data",
            "AI",
            "cloud",
            "marketing",
            "analytics"
        ]
    },
    {
        "service_id": "SVC149",
        "service_name": "Cloud Smart Home Toolkit",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home toolkit offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$",
        "tags": [
            "data",
            "health",
            "AI"
        ]
    },
    {
        "service_id": "SVC150",
        "service_name": "Cloud Finance Network",
        "category": "Finance",
        "description": "A state-of-the-art finance network offering cloud features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$",
        "tags": [
            "AI",
            "analytics",
            "health",
            "auto",
            "education"
        ]
    },
    {
        "service_id": "SVC151",
        "service_name": "Automated Retail Membership",
        "category": "Retail",
        "description": "A state-of-the-art retail membership offering automated features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$",
        "tags": [
            "health",
            "analytics",
            "data"
        ]
    },
    {
        "service_id": "SVC152",
        "service_name": "Ultimate Entertainment Advisory",
        "category": "Entertainment",
        "description": "A state-of-the-art entertainment advisory offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$",
        "tags": [
            "analytics",
            "finance",
            "marketing",
            "design",
            "cloud"
        ]
    },
    {
        "service_id": "SVC153",
        "service_name": "Enterprise Retail Toolkit",
        "category": "Retail",
        "description": "A state-of-the-art retail toolkit offering enterprise features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$",
        "tags": [
            "AI",
            "data",
            "home",
            "finance"
        ]
    },
    {
        "service_id": "SVC154",
        "service_name": "Pro Education Dashboard",
        "category": "Education",
        "description": "A state-of-the-art education dashboard offering pro features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$",
        "tags": [
            "security",
            "tech",
            "analytics",
            "SaaS",
            "AI"
        ]
    },
    {
        "service_id": "SVC155",
        "service_name": "Digital Retail Membership",
        "category": "Retail",
        "description": "A state-of-the-art retail membership offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$$",
        "tags": [
            "creative",
            "auto",
            "cloud",
            "marketing"
        ]
    },
    {
        "service_id": "SVC156",
        "service_name": "Basic Smart Home Suite",
        "category": "Smart Home",
        "description": "A state-of-the-art smart home suite offering basic features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$",
        "tags": [
            "health",
            "marketing",
            "creative",
            "finance"
        ]
    },
    {
        "service_id": "SVC157",
        "service_name": "Ultimate Technology Membership",
        "category": "Technology",
        "description": "A state-of-the-art technology membership offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$$$",
        "tags": [
            "marketing",
            "AI",
            "IoT",
            "analytics",
            "health"
        ]
    },
    {
        "service_id": "SVC158",
        "service_name": "Ultimate Finance Coaching",
        "category": "Finance",
        "description": "A state-of-the-art finance coaching offering ultimate features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$$",
        "tags": [
            "analytics",
            "IoT",
            "AI"
        ]
    },
    {
        "service_id": "SVC159",
        "service_name": "Creative Consulting Solutions",
        "category": "Consulting",
        "description": "A state-of-the-art consulting solutions offering creative features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$$$$",
        "tags": [
            "data",
            "marketing",
            "education",
            "business",
            "creative"
        ]
    },
    {
        "service_id": "SVC160",
        "service_name": "Personal Automotive Hub",
        "category": "Automotive",
        "description": "A state-of-the-art automotive hub offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "20-40",
        "price_range": "$",
        "tags": [
            "analytics",
            "marketing",
            "health",
            "AI",
            "SaaS"
        ]
    },
    {
        "service_id": "SVC161",
        "service_name": "Premium Health System",
        "category": "Health",
        "description": "A state-of-the-art health system offering premium features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-35",
        "price_range": "$",
        "tags": [
            "tech",
            "IoT",
            "security",
            "marketing",
            "cloud"
        ]
    },
    {
        "service_id": "SVC162",
        "service_name": "Smart Retail Dashboard",
        "category": "Retail",
        "description": "A state-of-the-art retail dashboard offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$$",
        "tags": [
            "analytics",
            "design",
            "marketing",
            "SaaS",
            "IoT"
        ]
    },
    {
        "service_id": "SVC163",
        "service_name": "Personal Property Toolkit",
        "category": "Property",
        "description": "A state-of-the-art property toolkit offering personal features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "25-50",
        "price_range": "$$$$",
        "tags": [
            "business",
            "marketing",
            "creative"
        ]
    },
    {
        "service_id": "SVC164",
        "service_name": "Smart Legal Coaching",
        "category": "Legal",
        "description": "A state-of-the-art legal coaching offering smart features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "18-65",
        "price_range": "$$$",
        "tags": [
            "AI",
            "creative",
            "design",
            "health",
            "IoT"
        ]
    },
    {
        "service_id": "SVC165",
        "service_name": "Digital Education Platform",
        "category": "Education",
        "description": "A state-of-the-art education platform offering digital features. Designed to improve efficiency, provide top-notch value, and cater to modern needs. Highly customizable and user-friendly.",
        "target_age_range": "All Ages",
        "price_range": "$$$",
        "tags": [
            "SaaS",
            "cloud",
            "security",
            "finance",
            "home"
        ]
    },
    {
        "service_id": "SVC166",
        "service_name": "Monthly Fiction Book Box",
        "category": "Books",
        "description": "A curated monthly box of the latest fiction bestsellers, delivered straight to your door with exclusive author notes and bookmarks.",
        "target_age_range": "All Ages",
        "price_range": "$$",
        "tags": [
            "books",
            "fiction",
            "reading",
            "subscription",
            "monthly"
        ]
    },
    {
        "service_id": "SVC167",
        "service_name": "Rare Book Appraisal Service",
        "category": "Consulting",
        "description": "Professional appraisal of rare, antique, and first-edition books by certified experts. Includes a detailed valuation report.",
        "target_age_range": "30-75",
        "price_range": "$$$",
        "tags": [
            "books",
            "rare",
            "appraisal",
            "antique",
            "valuation"
        ]
    },
    {
        "service_id": "SVC168",
        "service_name": "E-Book Premium Library",
        "category": "Digital Books",
        "description": "Unlimited digital access to over 500,000 e-books and audiobooks. Compatible with all e-readers, tablets, and smartphones.",
        "target_age_range": "18-65",
        "price_range": "$",
        "tags": [
            "e-book",
            "reading",
            "digital",
            "library",
            "audiobook"
        ]
    },
    {
        "service_id": "SVC169",
        "service_name": "Author Masterclass Series",
        "category": "Education",
        "description": "Learn the craft of writing from best-selling authors. Video lectures, writing prompts, and peer feedback sessions.",
        "target_age_range": "16-65",
        "price_range": "$$",
        "tags": [
            "writing",
            "education",
            "courses",
            "authors",
            "learning"
        ]
    },
    {
        "service_id": "SVC170",
        "service_name": "Academic Textbook Rental",
        "category": "Education",
        "description": "Rent physical or digital academic textbooks for a semester at a fraction of the cost of buying. Free return shipping included.",
        "target_age_range": "18-25",
        "price_range": "$",
        "tags": [
            "textbooks",
            "education",
            "rental",
            "university",
            "academic"
        ]
    }
]


# ──────────────────────────────────────────────
# 2. Document formatter
# ──────────────────────────────────────────────

def format_service_document(service: dict) -> str:
    """
    Converts a service dict into a rich, searchable text document.
    This is the text that will be embedded and retrieved by the RAG pipeline.
    """
    tags = ", ".join(service.get("tags", []))
    doc = (
        f"Service ID: {service['service_id']}\n"
        f"Name: {service['service_name']}\n"
        f"Category: {service['category']}\n"
        f"Description: {service['description']}\n"
        f"Target Age Range: {service.get('target_age_range', 'N/A')}\n"
        f"Price Range: {service.get('price_range', 'N/A')}\n"
        f"Tags: {tags}"
    )
    return doc


# ──────────────────────────────────────────────
# 3. Build KB: attach formatted docs & save JSON
# ──────────────────────────────────────────────

def build_knowledge_base(
    catalogue: list = None,
    output_path: str = None,
) -> list:
    if output_path is None:
        output_path = DEFAULT_KB_PATH
    """
    Formats service records and saves the KB to disk.

    Returns:
        List of service dicts (with 'document' field added).
    """
    if catalogue is None:
        catalogue = SERVICE_CATALOGUE

    kb = []
    for svc in catalogue:
        record = dict(svc)                              # shallow copy
        record["document"] = format_service_document(svc)
        kb.append(record)

    # Persist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print(f"Knowledge base built: {len(kb)} services → {output_path}")
    return kb


# ──────────────────────────────────────────────
# 4. KB loader (for other modules to import)
# ──────────────────────────────────────────────

def load_knowledge_base(path: str = None) -> list:
    if path is None:
        path = DEFAULT_KB_PATH
    """Load a previously built KB from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
if __name__ == "__main__":
    kb = build_knowledge_base()
    # Preview
    print("\n── Sample document ──")
    print(kb[0]["document"])