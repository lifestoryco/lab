export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      connections: {
        Row: {
          company: string | null
          company_normalized: string | null
          connected_on: string | null
          created_at: string
          email: string | null
          first_name: string | null
          full_name: string | null
          id: number
          last_name: string | null
          last_seen: string | null
          linkedin_url: string | null
          notes: string | null
          position: string | null
          seniority: string | null
          user_id: string
        }
        Insert: {
          company?: string | null
          company_normalized?: string | null
          connected_on?: string | null
          created_at?: string
          email?: string | null
          first_name?: string | null
          full_name?: string | null
          id?: number
          last_name?: string | null
          last_seen?: string | null
          linkedin_url?: string | null
          notes?: string | null
          position?: string | null
          seniority?: string | null
          user_id: string
        }
        Update: {
          company?: string | null
          company_normalized?: string | null
          connected_on?: string | null
          created_at?: string
          email?: string | null
          first_name?: string | null
          full_name?: string | null
          id?: number
          last_name?: string | null
          last_seen?: string | null
          linkedin_url?: string | null
          notes?: string | null
          position?: string | null
          seniority?: string | null
          user_id?: string
        }
        Relationships: []
      }
      dismissal_reasons: {
        Row: {
          code: string
          created_at: string
          description: string | null
          label: string
          sort_order: number
          user_id: string | null
        }
        Insert: {
          code: string
          created_at?: string
          description?: string | null
          label: string
          sort_order?: number
          user_id?: string | null
        }
        Update: {
          code?: string
          created_at?: string
          description?: string | null
          label?: string
          sort_order?: number
          user_id?: string | null
        }
        Relationships: []
      }
      levels_seed: {
        Row: {
          company: string
          default_level: string | null
          levels: Json
          notes: string | null
          source_url: string | null
          unknown: boolean
          updated_at: string
        }
        Insert: {
          company: string
          default_level?: string | null
          levels?: Json
          notes?: string | null
          source_url?: string | null
          unknown?: boolean
          updated_at?: string
        }
        Update: {
          company?: string
          default_level?: string | null
          levels?: Json
          notes?: string | null
          source_url?: string | null
          unknown?: boolean
          updated_at?: string
        }
        Relationships: []
      }
      offers: {
        Row: {
          annual_bonus_paid_history: string | null
          annual_bonus_target_pct: number | null
          base_salary: number
          benefits_delta: number | null
          company: string
          created_at: string
          equity_refresh_expected: boolean | null
          expires_at: string | null
          growth_signal: string | null
          id: number
          notes: string | null
          pto_days: number | null
          received_at: string
          remote_pct: number | null
          role_id: number | null
          rsu_cliff_months: number | null
          rsu_total_value: number | null
          rsu_vest_years: number | null
          rsu_vesting_schedule: string | null
          signing_bonus: number | null
          state_tax: string | null
          status: string | null
          title: string
          user_id: string
        }
        Insert: {
          annual_bonus_paid_history?: string | null
          annual_bonus_target_pct?: number | null
          base_salary: number
          benefits_delta?: number | null
          company: string
          created_at?: string
          equity_refresh_expected?: boolean | null
          expires_at?: string | null
          growth_signal?: string | null
          id?: number
          notes?: string | null
          pto_days?: number | null
          received_at: string
          remote_pct?: number | null
          role_id?: number | null
          rsu_cliff_months?: number | null
          rsu_total_value?: number | null
          rsu_vest_years?: number | null
          rsu_vesting_schedule?: string | null
          signing_bonus?: number | null
          state_tax?: string | null
          status?: string | null
          title: string
          user_id: string
        }
        Update: {
          annual_bonus_paid_history?: string | null
          annual_bonus_target_pct?: number | null
          base_salary?: number
          benefits_delta?: number | null
          company?: string
          created_at?: string
          equity_refresh_expected?: boolean | null
          expires_at?: string | null
          growth_signal?: string | null
          id?: number
          notes?: string | null
          pto_days?: number | null
          received_at?: string
          remote_pct?: number | null
          role_id?: number | null
          rsu_cliff_months?: number | null
          rsu_total_value?: number | null
          rsu_vest_years?: number | null
          rsu_vesting_schedule?: string | null
          signing_bonus?: number | null
          state_tax?: string | null
          status?: string | null
          title?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "offers_role_id_fkey"
            columns: ["role_id"]
            isOneToOne: false
            referencedRelation: "roles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "offers_role_id_fkey"
            columns: ["role_id"]
            isOneToOne: false
            referencedRelation: "weekly_improvement_corpus"
            referencedColumns: ["role_id"]
          },
        ]
      }
      outreach: {
        Row: {
          connection_id: number | null
          contact_role: string | null
          draft_message: string | null
          drafted_at: string
          id: number
          notes: string | null
          replied_at: string | null
          role_id: number | null
          sent_at: string | null
          target_role_id: number | null
          user_id: string
          warmth_score: number | null
        }
        Insert: {
          connection_id?: number | null
          contact_role?: string | null
          draft_message?: string | null
          drafted_at?: string
          id?: number
          notes?: string | null
          replied_at?: string | null
          role_id?: number | null
          sent_at?: string | null
          target_role_id?: number | null
          user_id: string
          warmth_score?: number | null
        }
        Update: {
          connection_id?: number | null
          contact_role?: string | null
          draft_message?: string | null
          drafted_at?: string
          id?: number
          notes?: string | null
          replied_at?: string | null
          role_id?: number | null
          sent_at?: string | null
          target_role_id?: number | null
          user_id?: string
          warmth_score?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "outreach_connection_id_fkey"
            columns: ["connection_id"]
            isOneToOne: false
            referencedRelation: "connections"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "outreach_role_id_fkey"
            columns: ["role_id"]
            isOneToOne: false
            referencedRelation: "roles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "outreach_role_id_fkey"
            columns: ["role_id"]
            isOneToOne: false
            referencedRelation: "weekly_improvement_corpus"
            referencedColumns: ["role_id"]
          },
          {
            foreignKeyName: "outreach_target_role_id_fkey"
            columns: ["target_role_id"]
            isOneToOne: false
            referencedRelation: "roles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "outreach_target_role_id_fkey"
            columns: ["target_role_id"]
            isOneToOne: false
            referencedRelation: "weekly_improvement_corpus"
            referencedColumns: ["role_id"]
          },
        ]
      }
      profiles: {
        Row: {
          comp_floor_max: number | null
          comp_floor_min: number | null
          created_at: string
          display_name: string | null
          id: string
          preferred_archetypes: string[] | null
          updated_at: string
        }
        Insert: {
          comp_floor_max?: number | null
          comp_floor_min?: number | null
          created_at?: string
          display_name?: string | null
          id: string
          preferred_archetypes?: string[] | null
          updated_at?: string
        }
        Update: {
          comp_floor_max?: number | null
          comp_floor_min?: number | null
          created_at?: string
          display_name?: string | null
          id?: string
          preferred_archetypes?: string[] | null
          updated_at?: string
        }
        Relationships: []
      }
      role_events: {
        Row: {
          created_at: string
          event_type: Database["public"]["Enums"]["role_event_type"]
          id: number
          payload: Json
          role_id: number
          user_id: string
        }
        Insert: {
          created_at?: string
          event_type: Database["public"]["Enums"]["role_event_type"]
          id?: number
          payload?: Json
          role_id: number
          user_id: string
        }
        Update: {
          created_at?: string
          event_type?: Database["public"]["Enums"]["role_event_type"]
          id?: number
          payload?: Json
          role_id?: number
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "role_events_role_id_fkey"
            columns: ["role_id"]
            isOneToOne: false
            referencedRelation: "roles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "role_events_role_id_fkey"
            columns: ["role_id"]
            isOneToOne: false
            referencedRelation: "weekly_improvement_corpus"
            referencedColumns: ["role_id"]
          },
        ]
      }
      roles: {
        Row: {
          comp_confidence: number | null
          comp_currency: string | null
          comp_max: number | null
          comp_min: number | null
          comp_source: string | null
          company: string | null
          discovered_at: string
          fit_score: number | null
          id: number
          jd_parsed: Json | null
          jd_parsed_at: string | null
          jd_raw: string | null
          lane: string | null
          location: string | null
          notes: string | null
          posted_at: string | null
          remote: boolean | null
          score_stage: number | null
          score_stage1: number | null
          score_stage2: number | null
          source: string | null
          status: Database["public"]["Enums"]["role_status"]
          title: string | null
          updated_at: string
          url: string
          user_id: string
        }
        Insert: {
          comp_confidence?: number | null
          comp_currency?: string | null
          comp_max?: number | null
          comp_min?: number | null
          comp_source?: string | null
          company?: string | null
          discovered_at?: string
          fit_score?: number | null
          id?: number
          jd_parsed?: Json | null
          jd_parsed_at?: string | null
          jd_raw?: string | null
          lane?: string | null
          location?: string | null
          notes?: string | null
          posted_at?: string | null
          remote?: boolean | null
          score_stage?: number | null
          score_stage1?: number | null
          score_stage2?: number | null
          source?: string | null
          status?: Database["public"]["Enums"]["role_status"]
          title?: string | null
          updated_at?: string
          url: string
          user_id: string
        }
        Update: {
          comp_confidence?: number | null
          comp_currency?: string | null
          comp_max?: number | null
          comp_min?: number | null
          comp_source?: string | null
          company?: string | null
          discovered_at?: string
          fit_score?: number | null
          id?: number
          jd_parsed?: Json | null
          jd_parsed_at?: string | null
          jd_raw?: string | null
          lane?: string | null
          location?: string | null
          notes?: string | null
          posted_at?: string | null
          remote?: boolean | null
          score_stage?: number | null
          score_stage1?: number | null
          score_stage2?: number | null
          source?: string | null
          status?: Database["public"]["Enums"]["role_status"]
          title?: string | null
          updated_at?: string
          url?: string
          user_id?: string
        }
        Relationships: []
      }
      stories: {
        Row: {
          context: string
          created_at: string
          headline: string
          id: string
          lane: string
          metric: string
          source_of_truth: string
          updated_at: string
          user_id: string
        }
        Insert: {
          context: string
          created_at?: string
          headline: string
          id: string
          lane: string
          metric: string
          source_of_truth: string
          updated_at?: string
          user_id: string
        }
        Update: {
          context?: string
          created_at?: string
          headline?: string
          id?: string
          lane?: string
          metric?: string
          source_of_truth?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      pipeline_counts: {
        Row: {
          n: number | null
          status: Database["public"]["Enums"]["role_status"] | null
          user_id: string | null
        }
        Relationships: []
      }
      weekly_improvement_corpus: {
        Row: {
          comp_max: number | null
          comp_min: number | null
          comp_source: string | null
          company: string | null
          event_at: string | null
          event_id: number | null
          event_type: Database["public"]["Enums"]["role_event_type"] | null
          fit_score: number | null
          lane: string | null
          payload: Json | null
          role_id: number | null
          score_stage1: number | null
          score_stage2: number | null
          title: string | null
          user_id: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      role_event_type:
        | "status_change"
        | "dismissed"
        | "applied"
        | "offer_received"
        | "rejected"
        | "withdrew"
        | "note_added"
        | "tailor_queued"
        | "resume_generated"
      role_status:
        | "discovered"
        | "scored"
        | "resume_generated"
        | "applied"
        | "responded"
        | "contact"
        | "interviewing"
        | "offer"
        | "rejected"
        | "withdrawn"
        | "no_apply"
        | "closed"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      role_event_type: [
        "status_change",
        "dismissed",
        "applied",
        "offer_received",
        "rejected",
        "withdrew",
        "note_added",
        "tailor_queued",
        "resume_generated",
      ],
      role_status: [
        "discovered",
        "scored",
        "resume_generated",
        "applied",
        "responded",
        "contact",
        "interviewing",
        "offer",
        "rejected",
        "withdrawn",
        "no_apply",
        "closed",
      ],
    },
  },
} as const
