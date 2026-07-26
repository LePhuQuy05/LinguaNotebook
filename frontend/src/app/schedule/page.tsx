"use client";

import { useState } from "react";
import { ScheduleBuilder } from "../../components/schedule/ScheduleBuilder";

export default function SchedulePage() {
  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="font-heading text-heading-xl mb-6">Study Schedule</h1>
      <ScheduleBuilder />
    </div>
  );
}
