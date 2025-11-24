import { FileText, MessageSquare, Zap } from 'lucide-react';

interface LandingPageProps {
  onShowLogin: () => void;
  onShowSignup: () => void;
}

export function LandingPage({ onShowLogin, onShowSignup }: LandingPageProps) {
  return (
    <div className="flex h-screen flex-col bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-900 dark:via-blue-950 dark:to-purple-950">
      <header className="flex h-16 items-center justify-between border-b border-border/40 bg-white/60 backdrop-blur-sm px-6 dark:bg-gray-950/60">
        <div className="flex items-center gap-3">
          <img
            src="/assets/promtree_dark.svg"
            alt="PROMTREE"
            className="h-6 dark:block hidden"
          />
          <img
            src="/assets/promtree_color.svg"
            alt="PROMTREE"
            className="h-6 dark:hidden block"
          />
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onShowLogin}
            className="rounded-lg border border-input px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
          >
            로그인
          </button>
          <button
            onClick={onShowSignup}
            className="rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-4 py-2 text-sm font-medium text-white hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg shadow-blue-500/30"
          >
            가입하기
          </button>
        </div>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        <div className="max-w-6xl w-full">
          {/* Hero Section */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 rounded-full bg-blue-100 dark:bg-blue-900/30 px-4 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300 mb-6">
              <Zap className="h-4 w-4" />
              AI 기반 지식 관리
            </div>
            <h2 className="text-5xl font-bold tracking-tight sm:text-7xl bg-gradient-to-r from-gray-900 via-blue-800 to-purple-800 dark:from-white dark:via-blue-200 dark:to-purple-200 bg-clip-text text-transparent mb-6">
              RAG 기반<br />지식 관리 플랫폼
            </h2>
            <p className="mt-6 text-xl leading-8 text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
              PDF 문서를 업로드하고 AI와 대화하며 필요한 정보를 빠르게 찾아보세요.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <button
                onClick={onShowSignup}
                className="group rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 px-8 py-4 text-base font-semibold text-white shadow-xl shadow-blue-500/30 hover:shadow-2xl hover:shadow-blue-500/40 hover:scale-105 transition-all"
              >
                무료로 시작하기
                <span className="inline-block ml-2 group-hover:translate-x-1 transition-transform">→</span>
              </button>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <div className="group bg-white/70 dark:bg-gray-900/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-200/50 dark:border-gray-700/50 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-xl transition-all">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 mb-4 group-hover:scale-110 transition-transform">
                <FileText className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                문서 업로드
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                TDS, MSDS 등 다양한 PDF 문서를 간편하게 업로드하고 관리하세요.
              </p>
            </div>

            <div className="group bg-white/70 dark:bg-gray-900/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-200/50 dark:border-gray-700/50 hover:border-purple-300 dark:hover:border-purple-600 hover:shadow-xl transition-all">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 mb-4 group-hover:scale-110 transition-transform">
                <MessageSquare className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                AI 대화
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                자연어로 질문하고 AI가 문서에서 정확한 답변을 찾아드립니다.
              </p>
            </div>

            <div className="group bg-white/70 dark:bg-gray-900/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-200/50 dark:border-gray-700/50 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-xl transition-all">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 mb-4 group-hover:scale-110 transition-transform">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                빠른 검색
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                벡터 검색과 그래프 기반 RAG로 순식간에 원하는 정보를 찾으세요.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
