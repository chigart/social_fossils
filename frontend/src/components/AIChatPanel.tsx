import { useAIChat } from "../hooks/useAIChat";
import { AIView } from "./AIView";

export function AIChatPanel({ active }: { active: boolean }) {
  const aiChat = useAIChat(active);
  return <AIView {...aiChat} />;
}
