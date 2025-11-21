import { useState } from "react";
import { login, signup, getUserInfo } from "../lib/api";
import { setToken } from "../lib/auth";
import type { useToast } from "../hooks/useToast";

interface LoginProps {
  onLogin: (email: string) => void;
  toast: ReturnType<typeof useToast>;
  isSignup?: boolean;
  onClose?: () => void;
}

export function Login({ onLogin, toast, isSignup: initialIsSignup = false, onClose }: LoginProps) {
  const [isSignup, setIsSignup] = useState(initialIsSignup);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isSignup) {
      const result = await signup({ email, password, username });
      if (result.success && result.data) {
        toast.success("회원가입 성공!");
        setToken(result.data.access_token);
        onLogin(email);
      } else {
        toast.error("회원가입 실패: " + (result.error || ""));
      }
    } else {
      const result = await login({ email, password });
      if (result.success && result.data) {
        toast.success("로그인 성공!");
        setToken(result.data.access_token);
        onLogin(email);
      } else {
        toast.error("로그인 실패: " + (result.error || ""));
      }
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="relative w-full max-w-md space-y-8 rounded-lg border border-border bg-card p-8">
        {onClose && (
          <button
            onClick={onClose}
            className="absolute right-4 top-4 rounded-md p-1 hover:bg-accent"
          >
            ✕
          </button>
        )}
        <div className="text-center">
          <h1 className="text-3xl font-bold">PROMTREE</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {isSignup ? "새 계정 만들기" : "로그인하여 계속하기"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">이메일</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">비밀번호</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              required
            />
          </div>

          {isSignup && (
            <div>
              <label className="block text-sm font-medium mb-2">사용자명</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2"
                required
              />
            </div>
          )}

          <button
            type="submit"
            className="w-full rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            {isSignup ? "회원가입" : "로그인"}
          </button>
        </form>

        <div className="text-center text-sm">
          <button
            onClick={() => setIsSignup(!isSignup)}
            className="text-primary hover:underline"
          >
            {isSignup ? "이미 계정이 있으신가요? 로그인" : "계정이 없으신가요? 회원가입"}
          </button>
        </div>
      </div>
    </div>
  );
}
