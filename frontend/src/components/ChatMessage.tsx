import { motion } from "framer-motion";
import { Bot, User } from "lucide-react";
import type { ReactNode } from "react";

interface ChatMessageProps {
  role: "user" | "assistant";
  children: ReactNode;
}

export default function ChatMessage({ role, children }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${
          isUser
            ? "border-accent/30 bg-accent/20 text-accent-light"
            : "border-navy-600 bg-navy-800 text-accent"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={`max-w-full flex-1 ${isUser ? "flex justify-end" : ""}`}
      >
        <div
          className={`rounded-xl border px-4 py-3 ${
            isUser
              ? "border-accent/25 bg-accent/10 text-slate-100"
              : "border-navy-700 bg-navy-900/90 text-slate-200"
          }`}
        >
          {children}
        </div>
      </div>
    </motion.div>
  );
}
