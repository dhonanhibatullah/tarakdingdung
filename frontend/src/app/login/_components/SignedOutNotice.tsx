"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";

import { useToast } from "@/hooks/use-toast";

export default function SignedOutNotice() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const fired = useRef(false);

  useEffect(() => {
    if (fired.current) {
      return;
    }
    if (searchParams.get("signedOut") === "1") {
      fired.current = true;
      toast.success("Signed out", "You have been signed out.");
      router.replace("/login");
    } else if (searchParams.get("sessionInvalid") === "1") {
      fired.current = true;
      toast.error("Session expired", "Please sign in again.");
      router.replace("/login");
    }
  }, [searchParams, router, toast]);

  return null;
}
