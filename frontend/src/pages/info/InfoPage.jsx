import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import Icon from "../../components/Icon";
import "./InfoPage.css";

/**
 * About / Contact / Privacy / Terms.
 *
 * The footer and navbar linked to all four, but none were registered in
 * App.jsx, so each rendered an empty page inside the chrome. They are static
 * copy with no data dependency, so they live here as one route parameterised by
 * slug rather than as four near-identical files.
 *
 * The copy describes what this build actually does. Where something is not
 * implemented — there is no payments processor and no newsletter backend — the
 * text says so rather than claiming a capability that does not exist.
 */

const SECTIONS = {
  about: {
    tag: "About us",
    title: "Plan India in one place",
    lead: "Yatrip brings hotels, food, attractions, transport and rentals together, so planning a trip across India does not mean six browser tabs and four different booking confirmations.",
    icon: "compass",
    blocks: [
      {
        icon: "hotel",
        title: "Stays that can actually be booked",
        body: "Hotels carry real room types, rate plans and an availability calendar. A reservation takes a hold on the inventory, then confirms — so a room you were shown is a room you get.",
      },
      {
        icon: "utensils",
        title: "Food, not just restaurant names",
        body: "Restaurants, cafés, dhabas, bakeries and street-food stalls, filterable by category, cuisine, price and whether they are open right now. Menus and vendor details live on the listing.",
      },
      {
        icon: "landmark",
        title: "Attractions with honest opening hours",
        body: "Monuments, temples, parks and museums with entry fees and timings, plus a photo credit on every image so you know what you are looking at.",
      },
      {
        icon: "bus",
        title: "Getting there and around",
        body: "Bus stands, metro, rail, airports, taxi and ferry points near you, on a map, with a route planner that draws the actual road route between two stops.",
      },
      {
        icon: "sparkles",
        title: "A planner that knows the data",
        body: "The AI assistant answers with live availability and geography rather than guesses. It runs on a retrieval-augmented agent over Yatrip's own listings and mapping data.",
      },
      {
        icon: "building",
        title: "Built for both sides of the table",
        body: "Travellers search and book; hotel, rental, food and attraction owners register their own listings and manage them from a dashboard. Both sides are first-class, not an afterthought.",
      },
    ],
    cta: { to: "/hotels", label: "Browse hotels", icon: "hotel" },
  },

  contact: {
    tag: "Contact",
    title: "Get in touch",
    lead: "The quickest route depends on what you need. Pick whichever fits.",
    icon: "mail",
    blocks: [
      {
        icon: "user",
        title: "Account & bookings",
        body: "A booking stuck in confirmed or held, a payment that looks wrong, or a profile that will not update. Open the booking from My Bookings first — it carries the full status history — and quote the booking reference.",
      },
      {
        icon: "building",
        title: "Listing your property",
        body: "Hotels, homestays, restaurants and attractions all go through the same owner dashboard. Register as an owner from the signup page, then add your first listing from My Hotels, My Rentals, My Food Places or My Attractions.",
      },
      {
        icon: "bug",
        title: "Reporting a wrong detail",
        body: "Address, coordinates, opening hours or a photo that does not match the place. These usually trace back to OpenStreetMap or Wikipedia data, so a correction upstream helps everyone, not just Yatrip.",
      },
      {
        icon: "shield",
        title: "Privacy & data requests",
        body: "Ask what data is held about your account, or ask for it to be deleted. The Privacy page explains exactly what is collected and where each piece comes from.",
      },
    ],
    note:
      "There is no support desk staffed around the clock yet. If something is time-critical — you are standing at a hotel that will not check you in — call the property directly; their number is on the listing.",
    cta: { to: "/hotels", label: "Find a stay", icon: "hotel" },
  },

  privacy: {
    tag: "Legal",
    title: "Privacy policy",
    lead: "What Yatrip stores, why, and what you can ask us to remove.",
    icon: "shield",
    updated: "Last updated: October 2026",
    blocks: [
      {
        icon: "user",
        title: "What you give us",
        body: "On signup: a username, an email address, a password (stored hashed, never in plain text) and optionally a phone number. If you register as a business owner, also your business name, type, address and GSTIN. Chat history and your saved booking references are stored against your account so you can pick them up on another device.",
      },
      {
        icon: "pin",
        title: "Location data",
        body: "Approximate location, only when you press the location button on the transport, food or attractions pages. It is sent to the API to sort results by distance and is not persisted on our side. The browser asks for permission; declining leaves everything else working.",
      },
      {
        icon: "globe",
        title: "Where place data comes from",
        body: "Attraction, food and transport data is derived from OpenStreetMap, Overpass, Nominatim and Wikipedia, fetched and cached server-side. Place photographs may come from OpenTripMap or Wikimedia Commons and keep their original licence and attribution.",
      },
      {
        icon: "mail",
        title: "Cookies",
        body: "Two HttpOnly cookies hold your access and refresh tokens, which is why signing in survives a page reload and cannot be read by client-side script. A third, readable cookie holds which account is signed in, purely so the navbar does not flash the signed-out state before the profile request returns.",
      },
      {
        icon: "sparkles",
        title: "AI assistant",
        body: "Messages you send the planner are sent to the configured language-model provider to produce a reply, and are stored with your session so the conversation can continue. Avoid putting personal details into a chat message.",
      },
      {
        icon: "shield",
        title: "Your choices",
        body: "You can clear your chat sessions from the sidebar in the AI planner, and you can ask for your account and its data to be deleted. Deleting the account removes your profile, listings, bookings and chat history. Aggregate, non-identifying counts derived from usage are not part of this and are not linked to you.",
      },
    ],
    cta: { to: "/contact", label: "Ask a data question", icon: "mail" },
  },

  terms: {
    tag: "Legal",
    title: "Terms of use",
    lead: "The practical rules for using Yatrip.",
    icon: "badgeCheck",
    updated: "Last updated: October 2026",
    blocks: [
      {
        icon: "search",
        title: "What Yatrip is",
        body: "A discovery and booking platform. Listing details — prices, availability, opening hours, photos, addresses — come from hotel and owner submissions and from open geographic data sources. Treat them as information to check rather than a guarantee.",
      },
      {
        icon: "wallet",
        title: "Payments",
        body: "This build does not integrate a payment processor. Reservation pricing and availability are exercised end to end, but no money moves through Yatrip, so no card or bank details are ever collected here.",
      },
      {
        icon: "calendar",
        title: "Bookings and holds",
        body: "Confirming a reservation takes a short-lived hold on the inventory and then confirms it. A hold you do not confirm expires on its own. If a booking cannot be completed you will not be charged, because there is no charge to make.",
      },
      {
        icon: "building",
        title: "Listings",
        body: "Owners are responsible for the accuracy of what they submit, including photos they do not have the right to publish. We may remove a listing that misleads travellers or infringes someone's rights. Listing on Yatrip is free; there is no commission.",
      },
      {
        icon: "globe",
        title: "Open data attribution",
        body: "Geographic data is © OpenStreetMap contributors, available under the Open Database License. Route geometry is served by OSRM; weather from Open-Meteo. Each retains its own licence and attribution.",
      },
      {
        icon: "shield",
        title: "Acceptable use",
        body: "Do not scrape the platform at volume, attempt to reach data belonging to another account, or use listings to mislead people. Automated imports run through the management commands rather than the public interface.",
      },
    ],
    cta: { to: "/register", label: "Create an account", icon: "userPlus" },
  },
};

const SLUGS = Object.keys(SECTIONS);

export default function InfoPage() {
  const { pathname } = useLocation();
  const slug = pathname.replace(/^\/+|\/+$/g, "").split("/")[0];
  const page = SECTIONS[slug];

  // Slugs are the route's only input; anything unregistered falls through to
  // the 404 route, so this is a belt-and-braces fallback.
  useEffect(() => {
    if (!page) return;
    document.title = `${page.tag} · Yatrip`;
    return () => { document.title = "Yatrip — Explore India Your Way"; };
  }, [page]);

  if (!page) return null;

  const others = SLUGS.filter((s) => s !== slug);

  return (
    <div className="info-page">
      <header className="info-hero">
        <div className="info-hero-inner">
          <span className="section-tag">
            <Icon name={page.icon} size={13} /> {page.tag}
          </span>
          <h1 className="info-title">{page.title}</h1>
          <p className="info-lead">{page.lead}</p>
          {page.updated && <p className="info-updated">{page.updated}</p>}
        </div>
      </header>

      <main className="info-body">
        <div className="info-blocks">
          {page.blocks.map((b, i) => (
            <section key={b.title} className="info-block" style={{ animationDelay: `${i * 0.06}s` }}>
              <span className="info-block-icon">
                <Icon name={b.icon} size={21} />
              </span>
              <div>
                <h2 className="info-block-title">{b.title}</h2>
                <p className="info-block-body">{b.body}</p>
              </div>
            </section>
          ))}
        </div>

        {page.note && (
          <aside className="info-note">
            <Icon name="zap" size={17} />
            <p>{page.note}</p>
          </aside>
        )}

        <div className="info-cta">
          <Link to={page.cta.to} className="yt-btn yt-btn--primary yt-btn--lg">
            {page.cta.label} <Icon name={page.cta.icon} size={17} />
          </Link>

          <nav className="info-switch" aria-label="Other pages">
            {others.map((s) => (
              <Link key={s} to={`/${s}`} className="info-switch-link">
                <Icon name={SECTIONS[s].icon} size={14} />
                {SECTIONS[s].tag}
              </Link>
            ))}
          </nav>
        </div>
      </main>
    </div>
  );
}