import { useState } from "react";
import { Mail, Lock, EyeOff, Eye } from "lucide-react";

function GitHubIcon({ size = 18, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-radial from-accent-primary via-accent-secondary to-orange-500">
      <div className="w-full max-w-[420px] bg-surface-primary rounded-lg shadow-[0_8px_32px_rgba(0,0,0,0.1)] px-8 py-12 flex flex-col gap-6 items-center">
        {/* Header */}
        <div className="flex flex-col gap-3 items-center w-full">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-b from-accent-primary to-accent-secondary" />
            <span className="font-heading text-2xl font-bold text-foreground-primary">
              Vibe
            </span>
          </div>
          <h1 className="font-heading text-[28px] font-bold text-foreground-primary text-center leading-tight">
            Welcome Back
          </h1>
          <p className="font-body text-sm text-foreground-secondary text-center">
            Sign in to continue to your account
          </p>
        </div>

        {/* Form */}
        <form
          className="flex flex-col gap-4 w-full"
          onSubmit={(e) => e.preventDefault()}
        >
          {/* Email */}
          <div className="flex flex-col gap-1.5">
            <label className="font-caption text-[13px] font-medium text-foreground-primary">
              Email
            </label>
            <div className="flex items-center gap-3 w-full h-11 px-4 rounded border border-border-subtle">
              <Mail size={18} className="text-foreground-secondary shrink-0" />
              <input
                type="email"
                placeholder="you@example.com"
                className="font-body text-sm text-foreground-primary placeholder:text-foreground-secondary w-full outline-none bg-transparent"
              />
            </div>
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5">
            <label className="font-caption text-[13px] font-medium text-foreground-primary">
              Password
            </label>
            <div className="flex items-center gap-3 w-full h-11 px-4 rounded border border-border-subtle">
              <Lock size={18} className="text-foreground-secondary shrink-0" />
              <input
                type={showPassword ? "text" : "password"}
                placeholder="••••••••••••"
                className="font-body text-sm text-foreground-primary placeholder:text-foreground-secondary w-full outline-none bg-transparent"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-foreground-secondary hover:text-foreground-primary transition-colors cursor-pointer"
              >
                {showPassword ? <Eye size={18} /> : <EyeOff size={18} />}
              </button>
            </div>
          </div>

          {/* Options Row */}
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 rounded-sm border border-border-subtle accent-accent-secondary"
              />
              <span className="font-body text-[13px] text-foreground-secondary">
                Remember me
              </span>
            </label>
            <a
              href="#"
              className="font-body text-[13px] text-accent-secondary hover:underline"
            >
              Forgot password?
            </a>
          </div>

          {/* Login Button */}
          <button
            type="submit"
            className="w-full h-12 rounded bg-gradient-to-b from-accent-primary to-accent-secondary font-heading text-base font-semibold text-foreground-primary shadow-[0_4px_12px_rgba(245,158,11,0.2)] hover:shadow-[0_6px_20px_rgba(245,158,11,0.35)] transition-shadow cursor-pointer"
          >
            Sign In
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-4 w-full">
          <div className="flex-1 h-px bg-border-subtle" />
          <span className="font-body text-[13px] text-foreground-secondary">
            or
          </span>
          <div className="flex-1 h-px bg-border-subtle" />
        </div>

        {/* Social Login */}
        <div className="flex gap-4 w-full">
          <button className="flex-1 h-11 rounded border border-border-subtle bg-surface-primary flex items-center justify-center gap-2 hover:bg-surface-secondary transition-colors cursor-pointer">
            <span className="font-data text-base font-bold text-[#4285F4]">
              G
            </span>
            <span className="font-body text-sm text-foreground-primary">
              Google
            </span>
          </button>
          <button className="flex-1 h-11 rounded border border-border-subtle bg-surface-primary flex items-center justify-center gap-2 hover:bg-surface-secondary transition-colors cursor-pointer">
            <GitHubIcon size={18} className="text-foreground-primary" />
            <span className="font-body text-sm text-foreground-primary">
              GitHub
            </span>
          </button>
        </div>

        {/* Signup */}
        <div className="flex gap-1 justify-center">
          <span className="font-body text-sm text-foreground-secondary">
            Don't have an account?
          </span>
          <a
            href="#"
            className="font-body text-sm font-semibold text-accent-secondary hover:underline"
          >
            Sign up
          </a>
        </div>
      </div>
    </div>
  );
}
