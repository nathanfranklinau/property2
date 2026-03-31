/**
 * GET /api/analysis/das?parcel_id=...
 *
 * Returns all development applications for a property.
 * Works for all councils with DA data.
 * For COMPLEX lots (BUP/GTP full complex view), returns all DAs across the plan.
 */

import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export type DevelopmentApplication = {
  application_number: string;
  description: string | null;
  application_type: string | null;
  application_group: string | null;
  lodgement_date: string | null;
  status: string | null;
  decision: string | null;
  suburb: string | null;
  location_address: string | null;
  source_system: string | null;
  // Dev.i fields
  assessment_level: string | null;
  use_categories: string | null;
  applicant: string | null;
  consultant: string | null;
  assessment_officer: string | null;
  appeal_result: string | null;
  // Dev.i milestones
  record_creation_date: string | null;
  commence_confirmation_date: string | null;
  properly_made_date: string | null;
  action_notice_response_date: string | null;
  confirmation_notice_sent_date: string | null;
  info_request_sent_date: string | null;
  final_response_received_date: string | null;
  public_notification_date: string | null;
  decision_notice_date: string | null;
  // ePathway fields
  decision_type: string | null;
  decision_date: string | null;
  decision_authority: string | null;
  responsible_officer: string | null;
  workflow_events: WorkflowEvent[] | null;
  epathway_id: number | null;
  // ePathway milestones
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
  // Parsed categories
  development_category: string | null;
  dwelling_type: string | null;
  unit_count: number | null;
  lot_split_from: number | null;
  lot_split_to: number | null;
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
      `SELECT DISTINCT ON (da.application_number, da.lodgement_date)
         da.application_number,
         da.description,
         da.application_type,
         da.application_group,
         da.lodgement_date::text,
         da.status,
         da.decision,
         da.suburb,
         da.location_address,
         da.source_system,
         da.assessment_level,
         da.use_categories,
         da.applicant,
         da.consultant,
         da.assessment_officer,
         da.appeal_result,
         da.record_creation_date::text,
         da.commence_confirmation_date::text,
         da.properly_made_date::text,
         da.action_notice_response_date::text,
         da.confirmation_notice_sent_date::text,
         da.info_request_sent_date::text,
         da.final_response_received_date::text,
         da.public_notification_date::text,
         da.decision_notice_date::text,
         da.decision_type,
         da.decision_date::text,
         da.decision_authority,
         da.responsible_officer,
         da.workflow_events,
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
         da.appeal_period_completed::text,
         da.development_category,
         da.dwelling_type,
         da.unit_count,
         da.lot_split_from,
         da.lot_split_to
       FROM parcels p
       JOIN development_application_addresses daa ON (
         CASE
           WHEN p.cadastre_lot = 'COMPLEX'
             THEN daa.cadastre_lotplan LIKE '%' || p.cadastre_plan
           ELSE
             daa.cadastre_lotplan = p.cadastre_lot || p.cadastre_plan
         END
       )
       JOIN development_applications da ON da.id = daa.application_id
       WHERE p.id = $1
       ORDER BY da.application_number, da.lodgement_date DESC NULLS LAST`,
      [parcelId]
    );

    if (result.rows.length === 0) {
      return NextResponse.json(null);
    }

    return NextResponse.json({ applications: result.rows });
  } catch (err) {
    console.error("DA list error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
