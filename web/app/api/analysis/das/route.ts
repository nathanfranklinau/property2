/**
 * GET /api/analysis/das?parcel_id=...
 *
 * Returns all development applications for a property.
 * Gold Coast only — returns null for other LGAs.
 * For COMPLEX lots (BUP/GTP full complex view), returns all DAs across the plan.
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export type DevelopmentApplication = {
  application_number: string;
  description: string | null;
  application_type: string | null;
  lodgement_date: string | null;
  status: string | null;
  suburb: string | null;
  location_address: string | null;
  lot_on_plan: string | null;
  lot_plan: string | null;
  decision_type: string | null;
  decision_date: string | null;
  decision_authority: string | null;
  responsible_officer: string | null;
  workflow_events: WorkflowEvent[] | null;
  development_category: string | null;
  dwelling_type: string | null;
  unit_count: number | null;
  lot_split_from: number | null;
  lot_split_to: number | null;
  assessment_level: string | null;
  epathway_id: number | null;
  // Milestone dates
  pre_assessment_started: string | null;
  pre_assessment_completed: string | null;
  confirmation_notice_started: string | null;
  confirmation_notice_completed: string | null;
  decision_started: string | null;
  decision_completed: string | null;
  decision_approved_started: string | null;
  decision_approved_completed: string | null;
  issue_decision_started: string | null;
  issue_decision_completed: string | null;
  appeal_period_started: string | null;
  appeal_period_completed: string | null;
};

export type WorkflowEvent = {
  date?: string;
  event?: string;
  description?: string;
};

export async function GET(req: NextRequest) {
  const parcelId = req.nextUrl.searchParams.get("parcel_id");

  if (!parcelId) {
    return NextResponse.json({ error: "parcel_id is required" }, { status: 400 });
  }

  try {
    const result = await db.query<DevelopmentApplication>(
      `SELECT
         da.application_number,
         da.description,
         da.application_type,
         da.lodgement_date::text,
         da.status,
         da.suburb,
         da.location_address,
         da.lot_on_plan,
         da.lot_plan,
         da.decision_type,
         da.decision_date::text,
         da.decision_authority,
         da.responsible_officer,
         da.workflow_events,
         da.development_category,
         da.dwelling_type,
         da.unit_count,
         da.lot_split_from,
         da.lot_split_to,
         da.assessment_level,
         da.epathway_id,
         da.pre_assessment_started::text,
         da.pre_assessment_completed::text,
         da.confirmation_notice_started::text,
         da.confirmation_notice_completed::text,
         da.decision_started::text,
         da.decision_completed::text,
         da.decision_approved_started::text,
         da.decision_approved_completed::text,
         da.issue_decision_started::text,
         da.issue_decision_completed::text,
         da.appeal_period_started::text,
         da.appeal_period_completed::text
       FROM parcels p
       JOIN goldcoast_dev_applications da
         ON (CASE
               WHEN p.cadastre_lot = 'COMPLEX' THEN da.lot_plan LIKE '%' || p.cadastre_plan
               ELSE da.lot_plan = p.cadastre_lot || p.cadastre_plan
             END)
       WHERE p.id = $1
         AND p.lga_name ILIKE '%gold coast%'
       ORDER BY da.lodgement_date DESC NULLS LAST`,
      [parcelId]
    );

    if (result.rows.length === 0) {
      // Check if this is Gold Coast at all
      const check = await db.query(
        `SELECT 1 FROM parcels WHERE id = $1 AND lga_name ILIKE '%gold coast%'`,
        [parcelId]
      );
      if (check.rows.length === 0) return NextResponse.json(null);
    }

    return NextResponse.json({ applications: result.rows });
  } catch (err) {
    console.error("DA list error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
