/**
 * GET /api/address/suggest?q=12 Smith Street, Sunny
 *
 * Returns up to 8 address suggestions from the GNAF dataset.
 * Replaces Google Places Autocomplete to eliminate per-keystroke API costs.
 *
 * Input parsing:
 *   - Requires a leading street number (e.g. "12" or "12A")
 *   - Street name prefix matched against gnaf_data_street_locality.street_name
 *   - Optional locality after a comma (e.g. ", Sunnybank")
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

const STREET_TYPES = new Set([
  "STREET",
  "ST",
  "ROAD",
  "RD",
  "AVENUE",
  "AVE",
  "DRIVE",
  "DR",
  "COURT",
  "CT",
  "CRESCENT",
  "CRES",
  "LANE",
  "LN",
  "PLACE",
  "PL",
  "TERRACE",
  "TCE",
  "CLOSE",
  "CL",
  "CIRCUIT",
  "CCT",
  "PARADE",
  "PDE",
  "WAY",
  "BOULEVARD",
  "BLVD",
  "ESPLANADE",
  "ESP",
  "HIGHWAY",
  "HWY",
  "GROVE",
  "GR",
  "SQUARE",
  "SQ",
  "RISE",
  "MEWS",
  "WALK",
  "TRACK",
  "OUTLOOK",
  "VIEW",
]);

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q")?.trim() ?? "";
  if (q.length < 4) {
    return NextResponse.json([]);
  }

  const [streetPart, ...localityParts] = q.split(",");
  const localityInput = localityParts.join(",").trim();

  // Extract leading street number (with optional suffix like "12A")
  const match = streetPart.trim().match(/^(\d+)([A-Za-z]?)\s+(.+)/);
  if (!match) {
    return NextResponse.json([]);
  }

  const streetNumber = parseInt(match[1], 10);
  const streetNameInput = match[3].trim().toUpperCase();

  // Strip trailing street-type words so "SMITH STREET" → "SMITH"
  const words = streetNameInput.split(/\s+/);
  while (words.length > 1 && STREET_TYPES.has(words[words.length - 1])) {
    words.pop();
  }
  const streetNamePrefix = words.join(" ");

  const params: (string | number)[] = [streetNumber, streetNamePrefix + "%"];
  let localityClause = "";

  if (localityInput.length >= 2) {
    const cleanLocality = localityInput
      .replace(/\b(QLD|NSW|VIC|SA|WA|TAS|NT|ACT)\b/gi, "")
      .replace(/\d{4}/, "")
      .trim();
    if (cleanLocality.length >= 2) {
      params.push(cleanLocality.toUpperCase() + "%");
      localityClause = `AND l.locality_name LIKE $${params.length}`;
    }
  }

  const query = `
    SELECT DISTINCT ON (ad.number_first, ad.number_first_suffix, sl.street_name, sl.street_type_code, l.locality_name)
      CONCAT(
        ad.number_first,
        COALESCE(UPPER(ad.number_first_suffix), ''),
        ' ',
        INITCAP(sl.street_name),
        COALESCE(' ' || INITCAP(st.name), ''),
        ', ',
        INITCAP(l.locality_name),
        ' ',
        s.state_abbreviation,
        ' ',
        COALESCE(ad.postcode, l.primary_postcode, '')
      ) AS display
    FROM gnaf_data_address_detail ad
    JOIN gnaf_data_street_locality sl ON sl.street_locality_pid = ad.street_locality_pid
    JOIN gnaf_data_locality l ON l.locality_pid = ad.locality_pid
    JOIN gnaf_data_state s ON s.state_pid = l.state_pid
    LEFT JOIN gnaf_data_street_type_aut st ON st.code = sl.street_type_code
    WHERE s.state_abbreviation = 'QLD'
      AND ad.date_retired IS NULL
      AND ad.number_first IS NOT NULL
      AND ad.number_first = $1
      AND sl.street_name LIKE $2
      ${localityClause}
    ORDER BY ad.number_first, ad.number_first_suffix, sl.street_name, sl.street_type_code, l.locality_name
    LIMIT 8
  `;

  const { rows } = await db.query(query, params);
  return NextResponse.json(
    rows.map((r: { display: string }) => r.display)
  );
}
