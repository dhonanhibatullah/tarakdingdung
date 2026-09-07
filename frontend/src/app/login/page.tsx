import type { Metadata } from "next";
import { CircleDollarSign } from "lucide-react";
import { Suspense } from "react";

import { APP_NAME } from "@/config/app";
import { getAppVersion } from "@/lib/api/version";

import LoginForm from "./_components/LoginForm";
import SignedOutNotice from "./_components/SignedOutNotice";

export const metadata: Metadata = {
  title: "Sign in — Tarakdingdung",
};

export default async function LoginPage() {
  const version = await getAppVersion();

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <div className="bg-background flex min-h-screen flex-1 flex-col px-6 py-10 sm:px-10 lg:w-[42%] lg:px-16 lg:py-12">
        <div className="flex flex-1 flex-col justify-center">
          <div className="mx-auto w-full max-w-sm lg:mx-0">
            <div className="flex items-center gap-2">
              <CircleDollarSign
                aria-hidden="true"
                className="text-primary size-9"
              />
              <span className="font-display text-foreground text-xl tracking-wide">
                {APP_NAME}
              </span>
            </div>

            <h1 className="font-display text-foreground mt-8 text-4xl tracking-wide">
              Sign in
            </h1>
            <p className="text-muted-foreground mt-2 text-sm">
              Enter your username and password to reach the console.
            </p>

            <div className="mt-8">
              <LoginForm />
            </div>

            <Suspense fallback={null}>
              <SignedOutNotice />
            </Suspense>
          </div>
        </div>

        <div className="text-muted-foreground flex w-full items-center justify-between gap-4 text-xs">
          <p>Automated crypto trading engine</p>
          {version ? <p>{version}</p> : null}
        </div>
      </div>

      <div className="bg-background hidden p-4 lg:flex lg:w-[58%]">
        <div className="bg-primary/90 w-full rounded-3xl" />
      </div>
    </div>
  );
}
