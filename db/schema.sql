--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5 (Homebrew)
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: address_validation_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.address_validation_cache (
    id integer NOT NULL,
    input_address text NOT NULL,
    place_id character varying(255),
    formatted_address text,
    street_number character varying(20),
    route character varying(200),
    locality character varying(100),
    administrative_area character varying(10),
    postal_code character varying(10),
    latitude numeric(10,8),
    longitude numeric(11,8),
    bounds_low_lat numeric(10,8),
    bounds_low_lng numeric(11,8),
    bounds_high_lat numeric(10,8),
    bounds_high_lng numeric(11,8),
    feature_size_meters numeric(8,2),
    validation_granularity character varying(50),
    address_complete boolean,
    possible_next_action character varying(20),
    is_residential boolean,
    is_business boolean,
    raw_response jsonb,
    queried_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE address_validation_cache; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.address_validation_cache IS 'Cache of Google Address Validation API responses. Staleness window configured in web/lib/address-validation.ts.';


--
-- Name: address_validation_cache_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.address_validation_cache_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: address_validation_cache_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.address_validation_cache_id_seq OWNED BY public.address_validation_cache.id;


--
-- Name: gnaf_admin_lga; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_admin_lga (
    id integer NOT NULL,
    lg_ply_pid character varying(15),
    lga_pid character varying(15),
    lga_name character varying(75) NOT NULL,
    abb_name character varying(50),
    state character(3) NOT NULL,
    dt_create date,
    geom public.geometry(MultiPolygon,7844)
);


--
-- Name: admin_lga_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admin_lga_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admin_lga_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admin_lga_id_seq OWNED BY public.gnaf_admin_lga.id;


--
-- Name: gnaf_admin_localities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_admin_localities (
    id integer NOT NULL,
    lc_ply_pid character varying(15),
    loc_pid character varying(15),
    loc_name character varying(50) NOT NULL,
    loc_class character varying(20),
    state character(3) NOT NULL,
    dt_create date,
    geom public.geometry(MultiPolygon,7844)
);


--
-- Name: admin_localities_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admin_localities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admin_localities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admin_localities_id_seq OWNED BY public.gnaf_admin_localities.id;


--
-- Name: gnaf_admin_state_boundaries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_admin_state_boundaries (
    id integer NOT NULL,
    st_ply_pid character varying(15),
    state_pid character varying(15),
    dt_create date,
    dt_retire date,
    geom public.geometry(MultiPolygon,7844)
);


--
-- Name: admin_state_boundaries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admin_state_boundaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admin_state_boundaries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admin_state_boundaries_id_seq OWNED BY public.gnaf_admin_state_boundaries.id;


--
-- Name: gnaf_admin_wards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_admin_wards (
    id integer NOT NULL,
    wd_ply_pid character varying(15),
    ward_pid character varying(15),
    ward_name character varying(75) NOT NULL,
    lga_pid character varying(15),
    state character(3) NOT NULL,
    dt_create date,
    geom public.geometry(MultiPolygon,7844)
);


--
-- Name: admin_wards_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admin_wards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admin_wards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admin_wards_id_seq OWNED BY public.gnaf_admin_wards.id;


--
-- Name: gnaf_data_address_alias; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_alias (
    address_alias_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    principal_pid character varying(15) NOT NULL,
    alias_pid character varying(15) NOT NULL,
    alias_type_code character varying(10) NOT NULL,
    alias_comment character varying(200)
);


--
-- Name: gnaf_data_address_alias_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_alias_type_aut (
    code character varying(10) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(30)
);


--
-- Name: gnaf_data_address_change_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_change_type_aut (
    code character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(500)
);


--
-- Name: gnaf_data_address_default_geocode; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_default_geocode (
    address_default_geocode_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    address_detail_pid character varying(15) NOT NULL,
    geocode_type_code character varying(4) NOT NULL,
    longitude numeric(11,8),
    latitude numeric(10,8),
    geometry public.geometry(Point,7844)
);


--
-- Name: gnaf_data_address_detail; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_detail (
    address_detail_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_last_modified date,
    date_retired date,
    building_name character varying(200),
    lot_number_prefix character varying(2),
    lot_number character varying(5),
    lot_number_suffix character varying(2),
    flat_type_code character varying(7),
    flat_number_prefix character varying(2),
    flat_number numeric(5,0),
    flat_number_suffix character varying(2),
    level_type_code character varying(4),
    level_number_prefix character varying(2),
    level_number numeric(3,0),
    level_number_suffix character varying(2),
    number_first_prefix character varying(3),
    number_first numeric(6,0),
    number_first_suffix character varying(2),
    number_last_prefix character varying(3),
    number_last numeric(6,0),
    number_last_suffix character varying(2),
    street_locality_pid character varying(15),
    location_description character varying(45),
    locality_pid character varying(15) NOT NULL,
    alias_principal character(1),
    postcode character varying(4),
    private_street character varying(75),
    legal_parcel_id character varying(20),
    confidence numeric(1,0),
    address_site_pid character varying(15) NOT NULL,
    level_geocoded_code numeric(2,0) NOT NULL,
    property_pid character varying(15),
    gnaf_property_pid character varying(15),
    primary_secondary character varying(1)
);


--
-- Name: gnaf_data_address_feature; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_feature (
    address_feature_id character varying(16) NOT NULL,
    address_feature_pid character varying(16) NOT NULL,
    address_detail_pid character varying(15) NOT NULL,
    date_address_detail_created date NOT NULL,
    date_address_detail_retired date,
    address_change_type_code character varying(50)
);


--
-- Name: gnaf_data_address_mesh_block_2016; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_mesh_block_2016 (
    address_mesh_block_2016_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    address_detail_pid character varying(15) NOT NULL,
    mb_match_code character varying(15) NOT NULL,
    mb_2016_pid character varying(15) NOT NULL
);


--
-- Name: gnaf_data_address_mesh_block_2021; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_mesh_block_2021 (
    address_mesh_block_2021_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    address_detail_pid character varying(15) NOT NULL,
    mb_match_code character varying(15) NOT NULL,
    mb_2021_pid character varying(15) NOT NULL
);


--
-- Name: gnaf_data_address_site; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_site (
    address_site_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    address_type character varying(8),
    address_site_name character varying(200)
);


--
-- Name: gnaf_data_address_site_geocode; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_site_geocode (
    address_site_geocode_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    address_site_pid character varying(15),
    geocode_site_name character varying(200),
    geocode_site_description character varying(45),
    geocode_type_code character varying(4),
    reliability_code numeric(1,0) NOT NULL,
    boundary_extent numeric(7,0),
    planimetric_accuracy numeric(12,0),
    elevation numeric(7,0),
    longitude numeric(11,8),
    latitude numeric(10,8),
    geometry public.geometry(Point,7844)
);


--
-- Name: gnaf_data_address_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_address_type_aut (
    code character varying(8) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(30)
);


--
-- Name: gnaf_data_flat_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_flat_type_aut (
    code character varying(7) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(30)
);


--
-- Name: gnaf_data_geocode_reliability_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_geocode_reliability_aut (
    code numeric(1,0) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(100)
);


--
-- Name: gnaf_data_geocode_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_geocode_type_aut (
    code character varying(4) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(250)
);


--
-- Name: gnaf_data_geocoded_level_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_geocoded_level_type_aut (
    code numeric(2,0) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(70)
);


--
-- Name: gnaf_data_level_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_level_type_aut (
    code character varying(4) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(30)
);


--
-- Name: gnaf_data_locality; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_locality (
    locality_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    locality_name character varying(100) NOT NULL,
    primary_postcode character varying(4),
    locality_class_code character(1) NOT NULL,
    state_pid character varying(15) NOT NULL,
    gnaf_locality_pid character varying(15),
    gnaf_reliability_code numeric(1,0) NOT NULL
);


--
-- Name: gnaf_data_locality_alias; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_locality_alias (
    locality_alias_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    locality_pid character varying(15) NOT NULL,
    name character varying(100) NOT NULL,
    postcode character varying(4),
    alias_type_code character varying(10) NOT NULL,
    state_pid character varying(15) NOT NULL
);


--
-- Name: gnaf_data_locality_alias_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_locality_alias_type_aut (
    code character varying(10) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(100)
);


--
-- Name: gnaf_data_locality_class_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_locality_class_aut (
    code character(1) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(200)
);


--
-- Name: gnaf_data_locality_neighbour; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_locality_neighbour (
    locality_neighbour_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    locality_pid character varying(15) NOT NULL,
    neighbour_locality_pid character varying(15) NOT NULL
);


--
-- Name: gnaf_data_locality_point; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_locality_point (
    locality_point_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    locality_pid character varying(15) NOT NULL,
    planimetric_accuracy numeric(12,0),
    longitude numeric(11,8),
    latitude numeric(10,8)
);


--
-- Name: gnaf_data_mb_2016; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_mb_2016 (
    mb_2016_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    mb_2016_code character varying(15) NOT NULL
);


--
-- Name: gnaf_data_mb_2021; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_mb_2021 (
    mb_2021_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    mb_2021_code character varying(15) NOT NULL
);


--
-- Name: gnaf_data_mb_match_code_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_mb_match_code_aut (
    code character varying(15) NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(250)
);


--
-- Name: gnaf_data_primary_secondary; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_primary_secondary (
    primary_secondary_pid character varying(15) NOT NULL,
    primary_pid character varying(15) NOT NULL,
    secondary_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    ps_join_type_code numeric(2,0) NOT NULL,
    ps_join_comment character varying(500)
);


--
-- Name: gnaf_data_ps_join_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_ps_join_type_aut (
    code numeric(2,0) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(500)
);


--
-- Name: gnaf_data_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_state (
    state_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    state_name character varying(50) NOT NULL,
    state_abbreviation character varying(3) NOT NULL
);


--
-- Name: gnaf_data_street_class_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_street_class_aut (
    code character(1) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(200)
);


--
-- Name: gnaf_data_street_locality; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_street_locality (
    street_locality_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    street_class_code character(1) NOT NULL,
    street_name character varying(100) NOT NULL,
    street_type_code character varying(15),
    street_suffix_code character varying(15),
    locality_pid character varying(15) NOT NULL,
    gnaf_street_pid character varying(15),
    gnaf_street_confidence numeric(1,0),
    gnaf_reliability_code numeric(1,0) NOT NULL
);


--
-- Name: gnaf_data_street_locality_alias; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_street_locality_alias (
    street_locality_alias_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    street_locality_pid character varying(15) NOT NULL,
    street_name character varying(100) NOT NULL,
    street_type_code character varying(15),
    street_suffix_code character varying(15),
    alias_type_code character varying(10) NOT NULL
);


--
-- Name: gnaf_data_street_locality_alias_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_street_locality_alias_type_aut (
    code character varying(10) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(15)
);


--
-- Name: gnaf_data_street_locality_point; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_street_locality_point (
    street_locality_point_pid character varying(15) NOT NULL,
    date_created date NOT NULL,
    date_retired date,
    street_locality_pid character varying(15) NOT NULL,
    boundary_extent numeric(7,0),
    planimetric_accuracy numeric(12,0),
    longitude numeric(11,8),
    latitude numeric(10,8)
);


--
-- Name: gnaf_data_street_suffix_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_street_suffix_aut (
    code character varying(15) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(30)
);


--
-- Name: gnaf_data_street_type_aut; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gnaf_data_street_type_aut (
    code character varying(15) NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(15)
);


--
-- Name: goldcoast_dev_applications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.goldcoast_dev_applications (
    application_number text NOT NULL,
    description text,
    application_type text,
    lodgement_date date,
    status text,
    suburb text,
    location_address text,
    lot_on_plan text,
    pre_assessment_started date,
    pre_assessment_completed date,
    confirmation_notice_started date,
    confirmation_notice_completed date,
    decision_started date,
    decision_completed date,
    documents_summary jsonb DEFAULT '[]'::jsonb,
    first_scraped_at timestamp with time zone DEFAULT now() NOT NULL,
    last_scraped_at timestamp with time zone DEFAULT now() NOT NULL,
    detail_scraped_at timestamp with time zone,
    monitoring_status text DEFAULT 'active'::text NOT NULL,
    status_changed_at timestamp with time zone,
    epathway_id integer,
    workflow_events jsonb DEFAULT '[]'::jsonb,
    decision_type text,
    decision_date date,
    decision_authority text,
    responsible_officer text,
    decision_approved_started date,
    decision_approved_completed date,
    issue_decision_started date,
    issue_decision_completed date,
    appeal_period_started date,
    appeal_period_completed date,
    lot_plan text GENERATED ALWAYS AS (replace(regexp_replace(lot_on_plan, '(?i)^.*lot\s+'::text, ''::text), ' '::text, ''::text)) STORED,
    development_category text,
    dwelling_type text,
    unit_count integer,
    lot_split_from integer,
    lot_split_to integer,
    assessment_level text
);


--
-- Name: COLUMN goldcoast_dev_applications.monitoring_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.goldcoast_dev_applications.monitoring_status IS 'active = needs periodic re-checking; closed = terminal status reached, no further scraping needed';


--
-- Name: parcels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parcels (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cadastre_lot character varying(10) NOT NULL,
    cadastre_plan character varying(20) NOT NULL,
    state character varying(3) DEFAULT 'QLD'::character varying NOT NULL,
    lot_area_sqm numeric(12,2),
    frontage_m numeric(8,2),
    depth_m numeric(8,2),
    display_address character varying(500),
    geometry public.geometry(MultiPolygon,7844),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    lga_name character varying(200),
    zone_code character varying(50),
    zone_name character varying(200),
    property_type character varying(30),
    plan_prefix character varying(5),
    address_count integer,
    flat_types text[],
    building_name character varying(200),
    complex_geometry public.geometry(MultiPolygon,7844),
    complex_lot_count integer,
    tenure_type character varying(50)
);


--
-- Name: property_analysis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.property_analysis (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    parcel_id uuid NOT NULL,
    image_status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    analysis_status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    image_satellite_path character varying(500),
    main_house_size_sqm numeric(10,2),
    building_count integer,
    available_space_sqm numeric(10,2),
    pool_count_detected integer DEFAULT 0,
    pool_count_registered integer DEFAULT 0,
    pool_area_sqm numeric(10,2) DEFAULT 0,
    error_message text,
    analyzed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    image_satellite_masked_path character varying(500),
    image_mask2_path character varying(500),
    image_street_view_path character varying(500),
    image_styled_map_path character varying(500),
    building_footprints_geo jsonb,
    boundary_coords_gda94 jsonb,
    centroid_lat double precision,
    centroid_lon double precision,
    CONSTRAINT property_analysis_analysis_status_check CHECK (((analysis_status)::text = ANY ((ARRAY['pending'::character varying, 'detecting'::character varying, 'complete'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT property_analysis_image_status_check CHECK (((image_status)::text = ANY ((ARRAY['pending'::character varying, 'downloading'::character varying, 'complete'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: qld_cadastre_address; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_cadastre_address (
    id integer NOT NULL,
    lot character varying(5),
    plan character varying(10),
    lotplan character varying(15),
    unit_type character varying(5),
    unit_number character varying(6),
    unit_suffix character varying(2),
    floor_type character varying(5),
    floor_number character varying(5),
    floor_suffix character varying(2),
    property_name character varying(100),
    street_no_1 character varying(11),
    street_no_1_suffix character varying(2),
    street_no_2 character varying(11),
    street_no_2_suffix character varying(2),
    street_number character varying(23),
    street_name character varying(50),
    street_type character varying(21),
    street_suffix character varying(21),
    street_full character varying(100),
    locality character varying(41),
    local_authority character varying(41),
    state character varying(3),
    address character varying(300),
    address_status character varying(1),
    address_standard character varying(4),
    lotplan_status character varying(1),
    address_pid integer,
    geocode_type character varying(5),
    latitude numeric,
    longitude numeric,
    geometry public.geometry(Point,7844)
);


--
-- Name: qld_cadastre_address_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_cadastre_address_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_cadastre_address_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_cadastre_address_id_seq OWNED BY public.qld_cadastre_address.id;


--
-- Name: qld_cadastre_bup_lot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_cadastre_bup_lot (
    id integer NOT NULL,
    lotplan character varying(15),
    bup_lot character varying(5),
    bup_plan character varying(10),
    bup_lotplan character varying(15),
    lot_area_am integer
);


--
-- Name: qld_cadastre_bup_lot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_cadastre_bup_lot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_cadastre_bup_lot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_cadastre_bup_lot_id_seq OWNED BY public.qld_cadastre_bup_lot.id;


--
-- Name: qld_cadastre_natbdy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_cadastre_natbdy (
    id integer NOT NULL,
    linestyle integer,
    seg_num integer,
    par_num integer,
    geometry public.geometry(MultiLineString,7844)
);


--
-- Name: qld_cadastre_natbdy_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_cadastre_natbdy_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_cadastre_natbdy_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_cadastre_natbdy_id_seq OWNED BY public.qld_cadastre_natbdy.id;


--
-- Name: qld_cadastre_parcels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_cadastre_parcels (
    id integer NOT NULL,
    lot character varying(5),
    plan character varying(10),
    lotplan character varying(15),
    lot_area numeric,
    excl_area numeric,
    geometry public.geometry(MultiPolygon,7844),
    seg_num integer,
    par_num integer,
    segpar integer,
    par_ind integer,
    lot_volume numeric,
    surv_ind character varying(1),
    tenure character varying(40),
    prc integer,
    parish character varying(20),
    county character varying(16),
    lac integer,
    shire_name character varying(40),
    feat_name character varying(60),
    alias_name character varying(400),
    loc integer,
    locality character varying(30),
    parcel_typ character varying(24),
    cover_typ character varying(10),
    acc_code character varying(40),
    ca_area_sqm numeric,
    smis_map character varying(100)
);


--
-- Name: qld_cadastre_parcels_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_cadastre_parcels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_cadastre_parcels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_cadastre_parcels_id_seq OWNED BY public.qld_cadastre_parcels.id;


--
-- Name: qld_cadastre_road; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_cadastre_road (
    id integer NOT NULL,
    linestyle integer,
    seg_num integer,
    par_num integer,
    geometry public.geometry(MultiLineString,7844)
);


--
-- Name: qld_cadastre_road_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_cadastre_road_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_cadastre_road_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_cadastre_road_id_seq OWNED BY public.qld_cadastre_road.id;


--
-- Name: qld_goldcoast_airport_noise; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_airport_noise (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    sensitive_use_type text,
    buffer_source text,
    buffer_distance text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_airport_noise_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_airport_noise_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_airport_noise_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_airport_noise_id_seq OWNED BY public.qld_goldcoast_airport_noise.id;


--
-- Name: qld_goldcoast_buffer_area; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_buffer_area (
    id integer NOT NULL,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_buffer_area_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_buffer_area_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_buffer_area_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_buffer_area_id_seq OWNED BY public.qld_goldcoast_buffer_area.id;


--
-- Name: qld_goldcoast_building_height; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_building_height (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    height_in_metres text,
    storey_number text,
    label text,
    height_label text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_building_height_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_building_height_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_building_height_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_building_height_id_seq OWNED BY public.qld_goldcoast_building_height.id;


--
-- Name: qld_goldcoast_bushfire_hazard; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_bushfire_hazard (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_bushfire_hazard_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_bushfire_hazard_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_bushfire_hazard_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_bushfire_hazard_id_seq OWNED BY public.qld_goldcoast_bushfire_hazard.id;


--
-- Name: qld_goldcoast_dwelling_house_overlay; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_dwelling_house_overlay (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_dwelling_house_overlay_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_dwelling_house_overlay_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_dwelling_house_overlay_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_dwelling_house_overlay_id_seq OWNED BY public.qld_goldcoast_dwelling_house_overlay.id;


--
-- Name: qld_goldcoast_environmental; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_environmental (
    id integer NOT NULL,
    category text NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_environmental_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_environmental_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_environmental_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_environmental_id_seq OWNED BY public.qld_goldcoast_environmental.id;


--
-- Name: qld_goldcoast_flood; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_flood (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_flood_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_flood_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_flood_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_flood_id_seq OWNED BY public.qld_goldcoast_flood.id;


--
-- Name: qld_goldcoast_heritage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_heritage (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    lhr_id text,
    place_name text,
    assessment_id text,
    register_status text,
    qld_heritage_register text,
    heritage_protection_boundary text,
    adjoining_allotments text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_heritage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_heritage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_heritage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_heritage_id_seq OWNED BY public.qld_goldcoast_heritage.id;


--
-- Name: qld_goldcoast_heritage_proximity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_heritage_proximity (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    lhr_id text,
    lot_plan text,
    assessment_id text,
    place_name text,
    qld_heritage_register text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_heritage_proximity_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_heritage_proximity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_heritage_proximity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_heritage_proximity_id_seq OWNED BY public.qld_goldcoast_heritage_proximity.id;


--
-- Name: qld_goldcoast_minimum_lot_size; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_minimum_lot_size (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    mls text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_minimum_lot_size_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_minimum_lot_size_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_minimum_lot_size_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_minimum_lot_size_id_seq OWNED BY public.qld_goldcoast_minimum_lot_size.id;


--
-- Name: qld_goldcoast_party_house; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_party_house (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_party_house_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_party_house_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_party_house_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_party_house_id_seq OWNED BY public.qld_goldcoast_party_house.id;


--
-- Name: qld_goldcoast_residential_density; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_residential_density (
    id integer NOT NULL,
    lga_code integer,
    cat_desc text,
    ovl_cat text,
    ovl2_desc text,
    ovl2_cat text,
    residential_density text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_residential_density_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_residential_density_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_residential_density_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_residential_density_id_seq OWNED BY public.qld_goldcoast_residential_density.id;


--
-- Name: qld_goldcoast_zones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_goldcoast_zones (
    id integer NOT NULL,
    zone_precinct text,
    lvl1_zone text,
    lga_code integer,
    zone text,
    building_height text,
    bh_category text,
    geometry public.geometry(Geometry,7844)
);


--
-- Name: qld_goldcoast_zones_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_goldcoast_zones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_goldcoast_zones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_goldcoast_zones_id_seq OWNED BY public.qld_goldcoast_zones.id;


--
-- Name: qld_planning_zones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_planning_zones (
    id integer NOT NULL,
    zone_code character varying(50),
    zone_name character varying(200),
    planning_scheme character varying(200),
    lga character varying(200),
    geometry public.geometry(MultiPolygon,7844)
);


--
-- Name: qld_planning_zones_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_planning_zones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_planning_zones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_planning_zones_id_seq OWNED BY public.qld_planning_zones.id;


--
-- Name: qld_pools_registered; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qld_pools_registered (
    id integer NOT NULL,
    site_name character varying(200) NOT NULL,
    unit_number character varying(20),
    street_number character varying(20),
    street_name character varying(200),
    street_type character varying(50),
    suburb character varying(100),
    postcode character varying(4),
    number_of_pools integer,
    lga character varying(200),
    shared_pool_property character varying(10)
);


--
-- Name: qld_pools_registered_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.qld_pools_registered_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: qld_pools_registered_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.qld_pools_registered_id_seq OWNED BY public.qld_pools_registered.id;


--
-- Name: address_validation_cache id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_validation_cache ALTER COLUMN id SET DEFAULT nextval('public.address_validation_cache_id_seq'::regclass);


--
-- Name: gnaf_admin_lga id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_admin_lga ALTER COLUMN id SET DEFAULT nextval('public.admin_lga_id_seq'::regclass);


--
-- Name: gnaf_admin_localities id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_admin_localities ALTER COLUMN id SET DEFAULT nextval('public.admin_localities_id_seq'::regclass);


--
-- Name: gnaf_admin_state_boundaries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_admin_state_boundaries ALTER COLUMN id SET DEFAULT nextval('public.admin_state_boundaries_id_seq'::regclass);


--
-- Name: gnaf_admin_wards id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_admin_wards ALTER COLUMN id SET DEFAULT nextval('public.admin_wards_id_seq'::regclass);


--
-- Name: qld_cadastre_address id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_address ALTER COLUMN id SET DEFAULT nextval('public.qld_cadastre_address_id_seq'::regclass);


--
-- Name: qld_cadastre_bup_lot id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_bup_lot ALTER COLUMN id SET DEFAULT nextval('public.qld_cadastre_bup_lot_id_seq'::regclass);


--
-- Name: qld_cadastre_natbdy id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_natbdy ALTER COLUMN id SET DEFAULT nextval('public.qld_cadastre_natbdy_id_seq'::regclass);


--
-- Name: qld_cadastre_parcels id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_parcels ALTER COLUMN id SET DEFAULT nextval('public.qld_cadastre_parcels_id_seq'::regclass);


--
-- Name: qld_cadastre_road id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_road ALTER COLUMN id SET DEFAULT nextval('public.qld_cadastre_road_id_seq'::regclass);


--
-- Name: qld_goldcoast_airport_noise id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_airport_noise ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_airport_noise_id_seq'::regclass);


--
-- Name: qld_goldcoast_buffer_area id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_buffer_area ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_buffer_area_id_seq'::regclass);


--
-- Name: qld_goldcoast_building_height id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_building_height ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_building_height_id_seq'::regclass);


--
-- Name: qld_goldcoast_bushfire_hazard id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_bushfire_hazard ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_bushfire_hazard_id_seq'::regclass);


--
-- Name: qld_goldcoast_dwelling_house_overlay id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_dwelling_house_overlay ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_dwelling_house_overlay_id_seq'::regclass);


--
-- Name: qld_goldcoast_environmental id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_environmental ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_environmental_id_seq'::regclass);


--
-- Name: qld_goldcoast_flood id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_flood ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_flood_id_seq'::regclass);


--
-- Name: qld_goldcoast_heritage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_heritage ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_heritage_id_seq'::regclass);


--
-- Name: qld_goldcoast_heritage_proximity id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_heritage_proximity ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_heritage_proximity_id_seq'::regclass);


--
-- Name: qld_goldcoast_minimum_lot_size id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_minimum_lot_size ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_minimum_lot_size_id_seq'::regclass);


--
-- Name: qld_goldcoast_party_house id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_party_house ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_party_house_id_seq'::regclass);


--
-- Name: qld_goldcoast_residential_density id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_residential_density ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_residential_density_id_seq'::regclass);


--
-- Name: qld_goldcoast_zones id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_zones ALTER COLUMN id SET DEFAULT nextval('public.qld_goldcoast_zones_id_seq'::regclass);


--
-- Name: qld_planning_zones id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_planning_zones ALTER COLUMN id SET DEFAULT nextval('public.qld_planning_zones_id_seq'::regclass);


--
-- Name: qld_pools_registered id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_pools_registered ALTER COLUMN id SET DEFAULT nextval('public.qld_pools_registered_id_seq'::regclass);


--
-- Name: address_validation_cache address_validation_cache_input_address_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_validation_cache
    ADD CONSTRAINT address_validation_cache_input_address_key UNIQUE (input_address);


--
-- Name: address_validation_cache address_validation_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_validation_cache
    ADD CONSTRAINT address_validation_cache_pkey PRIMARY KEY (id);


--
-- Name: gnaf_admin_lga admin_lga_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_admin_lga
    ADD CONSTRAINT admin_lga_pkey PRIMARY KEY (id);


--
-- Name: gnaf_admin_localities admin_localities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_admin_localities
    ADD CONSTRAINT admin_localities_pkey PRIMARY KEY (id);


--
-- Name: gnaf_admin_state_boundaries admin_state_boundaries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_admin_state_boundaries
    ADD CONSTRAINT admin_state_boundaries_pkey PRIMARY KEY (id);


--
-- Name: gnaf_admin_wards admin_wards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_admin_wards
    ADD CONSTRAINT admin_wards_pkey PRIMARY KEY (id);


--
-- Name: gnaf_data_address_alias gnaf_data_address_alias_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_alias
    ADD CONSTRAINT gnaf_data_address_alias_pkey PRIMARY KEY (address_alias_pid);


--
-- Name: gnaf_data_address_alias_type_aut gnaf_data_address_alias_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_alias_type_aut
    ADD CONSTRAINT gnaf_data_address_alias_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_address_change_type_aut gnaf_data_address_change_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_change_type_aut
    ADD CONSTRAINT gnaf_data_address_change_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_address_default_geocode gnaf_data_address_default_geocode_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_default_geocode
    ADD CONSTRAINT gnaf_data_address_default_geocode_pkey PRIMARY KEY (address_default_geocode_pid);


--
-- Name: gnaf_data_address_detail gnaf_data_address_detail_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_detail
    ADD CONSTRAINT gnaf_data_address_detail_pkey PRIMARY KEY (address_detail_pid);


--
-- Name: gnaf_data_address_feature gnaf_data_address_feature_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_feature
    ADD CONSTRAINT gnaf_data_address_feature_pkey PRIMARY KEY (address_feature_id);


--
-- Name: gnaf_data_address_mesh_block_2016 gnaf_data_address_mesh_block_2016_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_mesh_block_2016
    ADD CONSTRAINT gnaf_data_address_mesh_block_2016_pkey PRIMARY KEY (address_mesh_block_2016_pid);


--
-- Name: gnaf_data_address_mesh_block_2021 gnaf_data_address_mesh_block_2021_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_mesh_block_2021
    ADD CONSTRAINT gnaf_data_address_mesh_block_2021_pkey PRIMARY KEY (address_mesh_block_2021_pid);


--
-- Name: gnaf_data_address_site_geocode gnaf_data_address_site_geocode_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_site_geocode
    ADD CONSTRAINT gnaf_data_address_site_geocode_pkey PRIMARY KEY (address_site_geocode_pid);


--
-- Name: gnaf_data_address_site gnaf_data_address_site_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_site
    ADD CONSTRAINT gnaf_data_address_site_pkey PRIMARY KEY (address_site_pid);


--
-- Name: gnaf_data_address_type_aut gnaf_data_address_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_address_type_aut
    ADD CONSTRAINT gnaf_data_address_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_flat_type_aut gnaf_data_flat_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_flat_type_aut
    ADD CONSTRAINT gnaf_data_flat_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_geocode_reliability_aut gnaf_data_geocode_reliability_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_geocode_reliability_aut
    ADD CONSTRAINT gnaf_data_geocode_reliability_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_geocode_type_aut gnaf_data_geocode_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_geocode_type_aut
    ADD CONSTRAINT gnaf_data_geocode_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_geocoded_level_type_aut gnaf_data_geocoded_level_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_geocoded_level_type_aut
    ADD CONSTRAINT gnaf_data_geocoded_level_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_level_type_aut gnaf_data_level_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_level_type_aut
    ADD CONSTRAINT gnaf_data_level_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_locality_alias gnaf_data_locality_alias_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_locality_alias
    ADD CONSTRAINT gnaf_data_locality_alias_pkey PRIMARY KEY (locality_alias_pid);


--
-- Name: gnaf_data_locality_alias_type_aut gnaf_data_locality_alias_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_locality_alias_type_aut
    ADD CONSTRAINT gnaf_data_locality_alias_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_locality_class_aut gnaf_data_locality_class_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_locality_class_aut
    ADD CONSTRAINT gnaf_data_locality_class_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_locality_neighbour gnaf_data_locality_neighbour_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_locality_neighbour
    ADD CONSTRAINT gnaf_data_locality_neighbour_pkey PRIMARY KEY (locality_neighbour_pid);


--
-- Name: gnaf_data_locality gnaf_data_locality_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_locality
    ADD CONSTRAINT gnaf_data_locality_pkey PRIMARY KEY (locality_pid);


--
-- Name: gnaf_data_locality_point gnaf_data_locality_point_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_locality_point
    ADD CONSTRAINT gnaf_data_locality_point_pkey PRIMARY KEY (locality_point_pid);


--
-- Name: gnaf_data_mb_2016 gnaf_data_mb_2016_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_mb_2016
    ADD CONSTRAINT gnaf_data_mb_2016_pkey PRIMARY KEY (mb_2016_pid);


--
-- Name: gnaf_data_mb_2021 gnaf_data_mb_2021_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_mb_2021
    ADD CONSTRAINT gnaf_data_mb_2021_pkey PRIMARY KEY (mb_2021_pid);


--
-- Name: gnaf_data_mb_match_code_aut gnaf_data_mb_match_code_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_mb_match_code_aut
    ADD CONSTRAINT gnaf_data_mb_match_code_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_primary_secondary gnaf_data_primary_secondary_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_primary_secondary
    ADD CONSTRAINT gnaf_data_primary_secondary_pkey PRIMARY KEY (primary_secondary_pid);


--
-- Name: gnaf_data_ps_join_type_aut gnaf_data_ps_join_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_ps_join_type_aut
    ADD CONSTRAINT gnaf_data_ps_join_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_state gnaf_data_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_state
    ADD CONSTRAINT gnaf_data_state_pkey PRIMARY KEY (state_pid);


--
-- Name: gnaf_data_street_class_aut gnaf_data_street_class_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_street_class_aut
    ADD CONSTRAINT gnaf_data_street_class_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_street_locality_alias gnaf_data_street_locality_alias_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_street_locality_alias
    ADD CONSTRAINT gnaf_data_street_locality_alias_pkey PRIMARY KEY (street_locality_alias_pid);


--
-- Name: gnaf_data_street_locality_alias_type_aut gnaf_data_street_locality_alias_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_street_locality_alias_type_aut
    ADD CONSTRAINT gnaf_data_street_locality_alias_type_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_street_locality gnaf_data_street_locality_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_street_locality
    ADD CONSTRAINT gnaf_data_street_locality_pkey PRIMARY KEY (street_locality_pid);


--
-- Name: gnaf_data_street_locality_point gnaf_data_street_locality_point_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_street_locality_point
    ADD CONSTRAINT gnaf_data_street_locality_point_pkey PRIMARY KEY (street_locality_point_pid);


--
-- Name: gnaf_data_street_suffix_aut gnaf_data_street_suffix_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_street_suffix_aut
    ADD CONSTRAINT gnaf_data_street_suffix_aut_pkey PRIMARY KEY (code);


--
-- Name: gnaf_data_street_type_aut gnaf_data_street_type_aut_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gnaf_data_street_type_aut
    ADD CONSTRAINT gnaf_data_street_type_aut_pkey PRIMARY KEY (code);


--
-- Name: goldcoast_dev_applications goldcoast_dev_applications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goldcoast_dev_applications
    ADD CONSTRAINT goldcoast_dev_applications_pkey PRIMARY KEY (application_number);


--
-- Name: parcels parcels_cadastre_lot_cadastre_plan_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcels
    ADD CONSTRAINT parcels_cadastre_lot_cadastre_plan_key UNIQUE (cadastre_lot, cadastre_plan);


--
-- Name: parcels parcels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcels
    ADD CONSTRAINT parcels_pkey PRIMARY KEY (id);


--
-- Name: property_analysis property_analysis_parcel_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.property_analysis
    ADD CONSTRAINT property_analysis_parcel_id_key UNIQUE (parcel_id);


--
-- Name: property_analysis property_analysis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.property_analysis
    ADD CONSTRAINT property_analysis_pkey PRIMARY KEY (id);


--
-- Name: qld_cadastre_address qld_cadastre_address_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_address
    ADD CONSTRAINT qld_cadastre_address_pkey PRIMARY KEY (id);


--
-- Name: qld_cadastre_bup_lot qld_cadastre_bup_lot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_bup_lot
    ADD CONSTRAINT qld_cadastre_bup_lot_pkey PRIMARY KEY (id);


--
-- Name: qld_cadastre_natbdy qld_cadastre_natbdy_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_natbdy
    ADD CONSTRAINT qld_cadastre_natbdy_pkey PRIMARY KEY (id);


--
-- Name: qld_cadastre_parcels qld_cadastre_parcels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_parcels
    ADD CONSTRAINT qld_cadastre_parcels_pkey PRIMARY KEY (id);


--
-- Name: qld_cadastre_road qld_cadastre_road_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_cadastre_road
    ADD CONSTRAINT qld_cadastre_road_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_airport_noise qld_goldcoast_airport_noise_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_airport_noise
    ADD CONSTRAINT qld_goldcoast_airport_noise_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_buffer_area qld_goldcoast_buffer_area_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_buffer_area
    ADD CONSTRAINT qld_goldcoast_buffer_area_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_building_height qld_goldcoast_building_height_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_building_height
    ADD CONSTRAINT qld_goldcoast_building_height_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_bushfire_hazard qld_goldcoast_bushfire_hazard_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_bushfire_hazard
    ADD CONSTRAINT qld_goldcoast_bushfire_hazard_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_dwelling_house_overlay qld_goldcoast_dwelling_house_overlay_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_dwelling_house_overlay
    ADD CONSTRAINT qld_goldcoast_dwelling_house_overlay_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_environmental qld_goldcoast_environmental_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_environmental
    ADD CONSTRAINT qld_goldcoast_environmental_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_flood qld_goldcoast_flood_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_flood
    ADD CONSTRAINT qld_goldcoast_flood_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_heritage qld_goldcoast_heritage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_heritage
    ADD CONSTRAINT qld_goldcoast_heritage_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_heritage_proximity qld_goldcoast_heritage_proximity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_heritage_proximity
    ADD CONSTRAINT qld_goldcoast_heritage_proximity_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_minimum_lot_size qld_goldcoast_minimum_lot_size_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_minimum_lot_size
    ADD CONSTRAINT qld_goldcoast_minimum_lot_size_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_party_house qld_goldcoast_party_house_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_party_house
    ADD CONSTRAINT qld_goldcoast_party_house_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_residential_density qld_goldcoast_residential_density_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_residential_density
    ADD CONSTRAINT qld_goldcoast_residential_density_pkey PRIMARY KEY (id);


--
-- Name: qld_goldcoast_zones qld_goldcoast_zones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_goldcoast_zones
    ADD CONSTRAINT qld_goldcoast_zones_pkey PRIMARY KEY (id);


--
-- Name: qld_planning_zones qld_planning_zones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_planning_zones
    ADD CONSTRAINT qld_planning_zones_pkey PRIMARY KEY (id);


--
-- Name: qld_pools_registered qld_pools_registered_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_pools_registered
    ADD CONSTRAINT qld_pools_registered_pkey PRIMARY KEY (id);


--
-- Name: qld_pools_registered qld_pools_registered_site_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.qld_pools_registered
    ADD CONSTRAINT qld_pools_registered_site_name_key UNIQUE (site_name);


--
-- Name: idx_address_validation_cache_queried_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_address_validation_cache_queried_at ON public.address_validation_cache USING btree (queried_at);


--
-- Name: idx_gc_da_application_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_application_type ON public.goldcoast_dev_applications USING btree (application_type);


--
-- Name: idx_gc_da_assessment_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_assessment_level ON public.goldcoast_dev_applications USING btree (assessment_level);


--
-- Name: idx_gc_da_development_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_development_category ON public.goldcoast_dev_applications USING btree (development_category);


--
-- Name: idx_gc_da_dwelling_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_dwelling_type ON public.goldcoast_dev_applications USING btree (dwelling_type);


--
-- Name: idx_gc_da_epathway_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_epathway_id ON public.goldcoast_dev_applications USING btree (epathway_id);


--
-- Name: idx_gc_da_lodgement_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_lodgement_date ON public.goldcoast_dev_applications USING btree (lodgement_date);


--
-- Name: idx_gc_da_lot_on_plan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_lot_on_plan ON public.goldcoast_dev_applications USING btree (lot_on_plan);


--
-- Name: idx_gc_da_lot_plan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_lot_plan ON public.goldcoast_dev_applications USING btree (lot_plan);


--
-- Name: idx_gc_da_monitoring_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_monitoring_status ON public.goldcoast_dev_applications USING btree (monitoring_status) WHERE (monitoring_status = 'active'::text);


--
-- Name: idx_gc_da_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_status ON public.goldcoast_dev_applications USING btree (status);


--
-- Name: idx_gc_da_suburb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gc_da_suburb ON public.goldcoast_dev_applications USING btree (suburb);


--
-- Name: idx_gnaf_address_detail_number_first; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_address_detail_number_first ON public.gnaf_data_address_detail USING btree (number_first);


--
-- Name: idx_gnaf_admin_lga_geom; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_admin_lga_geom ON public.gnaf_admin_lga USING gist (geom);


--
-- Name: idx_gnaf_admin_lga_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_admin_lga_state ON public.gnaf_admin_lga USING btree (state);


--
-- Name: idx_gnaf_admin_localities_geom; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_admin_localities_geom ON public.gnaf_admin_localities USING gist (geom);


--
-- Name: idx_gnaf_admin_localities_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_admin_localities_state ON public.gnaf_admin_localities USING btree (state);


--
-- Name: idx_gnaf_admin_state_boundaries_geom; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_admin_state_boundaries_geom ON public.gnaf_admin_state_boundaries USING gist (geom);


--
-- Name: idx_gnaf_admin_wards_geom; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_admin_wards_geom ON public.gnaf_admin_wards USING gist (geom);


--
-- Name: idx_gnaf_admin_wards_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_admin_wards_state ON public.gnaf_admin_wards USING btree (state);


--
-- Name: idx_gnaf_data_address_detail_address_site; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_address_detail_address_site ON public.gnaf_data_address_detail USING btree (address_site_pid);


--
-- Name: idx_gnaf_data_address_detail_legal_parcel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_address_detail_legal_parcel ON public.gnaf_data_address_detail USING btree (legal_parcel_id);


--
-- Name: idx_gnaf_data_address_detail_locality; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_address_detail_locality ON public.gnaf_data_address_detail USING btree (locality_pid);


--
-- Name: idx_gnaf_data_address_detail_postcode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_address_detail_postcode ON public.gnaf_data_address_detail USING btree (postcode);


--
-- Name: idx_gnaf_data_address_detail_street_locality; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_address_detail_street_locality ON public.gnaf_data_address_detail USING btree (street_locality_pid);


--
-- Name: idx_gnaf_data_default_geocode_address_detail; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_default_geocode_address_detail ON public.gnaf_data_address_default_geocode USING btree (address_detail_pid);


--
-- Name: idx_gnaf_data_default_geocode_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_default_geocode_geometry ON public.gnaf_data_address_default_geocode USING gist (geometry);


--
-- Name: idx_gnaf_data_locality_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_locality_name ON public.gnaf_data_locality USING btree (locality_name);


--
-- Name: idx_gnaf_data_locality_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_locality_state ON public.gnaf_data_locality USING btree (state_pid);


--
-- Name: idx_gnaf_data_site_geocode_address_site; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_site_geocode_address_site ON public.gnaf_data_address_site_geocode USING btree (address_site_pid);


--
-- Name: idx_gnaf_data_site_geocode_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_site_geocode_geometry ON public.gnaf_data_address_site_geocode USING gist (geometry);


--
-- Name: idx_gnaf_data_street_locality_locality; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_street_locality_locality ON public.gnaf_data_street_locality USING btree (locality_pid);


--
-- Name: idx_gnaf_data_street_locality_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gnaf_data_street_locality_name ON public.gnaf_data_street_locality USING btree (street_name);


--
-- Name: idx_goldcoast_airport_noise_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_airport_noise_geometry ON public.qld_goldcoast_airport_noise USING gist (geometry);


--
-- Name: idx_goldcoast_buffer_area_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_buffer_area_geometry ON public.qld_goldcoast_buffer_area USING gist (geometry);


--
-- Name: idx_goldcoast_building_height_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_building_height_geometry ON public.qld_goldcoast_building_height USING gist (geometry);


--
-- Name: idx_goldcoast_bushfire_hazard_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_bushfire_hazard_geometry ON public.qld_goldcoast_bushfire_hazard USING gist (geometry);


--
-- Name: idx_goldcoast_dwelling_house_overlay_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_dwelling_house_overlay_geometry ON public.qld_goldcoast_dwelling_house_overlay USING gist (geometry);


--
-- Name: idx_goldcoast_environmental_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_environmental_geometry ON public.qld_goldcoast_environmental USING gist (geometry);


--
-- Name: idx_goldcoast_flood_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_flood_geometry ON public.qld_goldcoast_flood USING gist (geometry);


--
-- Name: idx_goldcoast_heritage_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_heritage_geometry ON public.qld_goldcoast_heritage USING gist (geometry);


--
-- Name: idx_goldcoast_heritage_proximity_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_heritage_proximity_geometry ON public.qld_goldcoast_heritage_proximity USING gist (geometry);


--
-- Name: idx_goldcoast_minimum_lot_size_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_minimum_lot_size_geometry ON public.qld_goldcoast_minimum_lot_size USING gist (geometry);


--
-- Name: idx_goldcoast_party_house_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_party_house_geometry ON public.qld_goldcoast_party_house USING gist (geometry);


--
-- Name: idx_goldcoast_residential_density_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_residential_density_geometry ON public.qld_goldcoast_residential_density USING gist (geometry);


--
-- Name: idx_goldcoast_zones_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goldcoast_zones_geometry ON public.qld_goldcoast_zones USING gist (geometry);


--
-- Name: idx_parcels_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parcels_geometry ON public.parcels USING gist (geometry);


--
-- Name: idx_qld_cadastre_address_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_address_geometry ON public.qld_cadastre_address USING gist (geometry);


--
-- Name: idx_qld_cadastre_address_local_authority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_address_local_authority ON public.qld_cadastre_address USING btree (local_authority);


--
-- Name: idx_qld_cadastre_address_locality; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_address_locality ON public.qld_cadastre_address USING btree (locality);


--
-- Name: idx_qld_cadastre_address_lotplan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_address_lotplan ON public.qld_cadastre_address USING btree (lotplan);


--
-- Name: idx_qld_cadastre_address_plan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_address_plan ON public.qld_cadastre_address USING btree (plan);


--
-- Name: idx_qld_cadastre_address_plan_street_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_address_plan_street_number ON public.qld_cadastre_address USING btree (plan, street_number);


--
-- Name: idx_qld_cadastre_bup_lot_bup_lotplan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_bup_lot_bup_lotplan ON public.qld_cadastre_bup_lot USING btree (bup_lotplan);


--
-- Name: idx_qld_cadastre_bup_lot_lotplan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_bup_lot_lotplan ON public.qld_cadastre_bup_lot USING btree (lotplan);


--
-- Name: idx_qld_cadastre_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_geometry ON public.qld_cadastre_parcels USING gist (geometry);


--
-- Name: idx_qld_cadastre_lot_plan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_lot_plan ON public.qld_cadastre_parcels USING btree (lot, plan);


--
-- Name: idx_qld_cadastre_lotplan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_lotplan ON public.qld_cadastre_parcels USING btree (lotplan);


--
-- Name: idx_qld_cadastre_natbdy_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_natbdy_geometry ON public.qld_cadastre_natbdy USING gist (geometry);


--
-- Name: idx_qld_cadastre_parcels_lot_type_partial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_parcels_lot_type_partial ON public.qld_cadastre_parcels USING btree (lot, plan) WHERE ((parcel_typ)::text = 'Lot Type Parcel'::text);


--
-- Name: idx_qld_cadastre_parcels_plan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_parcels_plan ON public.qld_cadastre_parcels USING btree (plan);


--
-- Name: idx_qld_cadastre_road_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_cadastre_road_geometry ON public.qld_cadastre_road USING gist (geometry);


--
-- Name: idx_qld_pools_postcode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_pools_postcode ON public.qld_pools_registered USING btree (postcode);


--
-- Name: idx_qld_pools_suburb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_pools_suburb ON public.qld_pools_registered USING btree (suburb);


--
-- Name: idx_qld_zones_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_qld_zones_geometry ON public.qld_planning_zones USING gist (geometry);


--
-- Name: property_analysis property_analysis_parcel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.property_analysis
    ADD CONSTRAINT property_analysis_parcel_id_fkey FOREIGN KEY (parcel_id) REFERENCES public.parcels(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

