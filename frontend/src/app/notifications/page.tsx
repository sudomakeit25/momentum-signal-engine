"use client";

import { useState } from "react";
import { Bell, Send, Check, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const WEBHOOK_KEY = "mse-webhook-config";

interface WebhookConfig {
  url: string;
  platform: "discord" | "telegram" | "slack";
}

function loadConfig(): WebhookConfig {
  if (typeof window === "undefined") return { url: "", platform: "discord" };
  try {
    return JSON.parse(localStorage.getItem(WEBHOOK_KEY) || '{"url":"","platform":"discord"}');
  } catch {
    return { url: "", platform: "discord" };
  }
}

export default function NotificationsPage() {
  const [config, setConfig] = useState<WebhookConfig>(loadConfig);
  const [testStatus, setTestStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [notifyStatus, setNotifyStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [message, setMessage] = useState("");

  const saveConfig = (c: WebhookConfig) => {
    setConfig(c);
    localStorage.setItem(WEBHOOK_KEY, JSON.stringify(c));
  };

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const testWebhook = async () => {
    if (!config.url) return;
    setTestStatus("sending");
    try {
      const res = await fetch(
        `${apiBase}/webhook/test?url=${encodeURIComponent(config.url)}&platform=${config.platform}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (data.status === "sent") {
        setTestStatus("sent");
        setMessage("Test message sent successfully!");
      } else {
        setTestStatus("error");
        setMessage(data.message || "Failed to send test message");
      }
    } catch {
      setTestStatus("error");
      setMessage("Network error");
    }
  };

  const sendSignals = async () => {
    if (!config.url) return;
    setNotifyStatus("sending");
    try {
      const res = await fetch(
        `${apiBase}/webhook/notify?url=${encodeURIComponent(config.url)}&platform=${config.platform}&top=5`,
        { method: "POST" }
      );
      const data = await res.json();
      if (data.status === "sent") {
        setNotifyStatus("sent");
        setMessage(`Sent ${data.signals_count} signals!`);
      } else if (data.status === "no_signals") {
        setNotifyStatus("sent");
        setMessage("No signals to send right now");
      } else {
        setNotifyStatus("error");
        setMessage(data.message || "Failed to send signals");
      }
    } catch {
      setNotifyStatus("error");
      setMessage("Network error");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Bell className="h-5 w-5 text-cyan-400" />
        <h1 className="text-lg font-bold">Notifications</h1>
      </div>

      {/* Webhook config */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 space-y-4">
        <h2 className="text-sm font-semibold text-zinc-300">Webhook Configuration</h2>

        <div>
          <label className="mb-1 block text-xs text-zinc-500">Platform</label>
          <div className="flex gap-2">
            {(["discord", "telegram", "slack"] as const).map((p) => (
              <button
                key={p}
                onClick={() => saveConfig({ ...config, platform: p })}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors",
                  config.platform === p
                    ? "bg-cyan-600 text-white"
                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                )}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs text-zinc-500">
            {config.platform === "discord"
              ? "Discord Webhook URL"
              : config.platform === "telegram"
              ? "Telegram Bot API URL (https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>)"
              : "Slack Webhook URL"}
          </label>
          <input
            value={config.url}
            onChange={(e) => saveConfig({ ...config, url: e.target.value })}
            placeholder={
              config.platform === "discord"
                ? "https://discord.com/api/webhooks/..."
                : config.platform === "telegram"
                ? "https://api.telegram.org/bot.../sendMessage?chat_id=..."
                : "https://hooks.slack.com/services/..."
            }
            className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:border-cyan-500 focus:outline-none"
          />
        </div>

        {/* Status message */}
        {message && (
          <div
            className={cn(
              "flex items-center gap-2 rounded-md p-2 text-sm",
              testStatus === "sent" || notifyStatus === "sent"
                ? "bg-emerald-950/30 text-emerald-400"
                : "bg-red-950/30 text-red-400"
            )}
          >
            {testStatus === "sent" || notifyStatus === "sent" ? (
              <Check className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            {message}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            size="sm"
            variant="outline"
            onClick={testWebhook}
            disabled={!config.url || testStatus === "sending"}
          >
            {testStatus === "sending" ? "Sending..." : "Test Webhook"}
          </Button>
          <Button
            size="sm"
            onClick={sendSignals}
            disabled={!config.url || notifyStatus === "sending"}
            className="bg-cyan-600 hover:bg-cyan-700"
          >
            <Send className="mr-1 h-3 w-3" />
            {notifyStatus === "sending" ? "Sending..." : "Send Current Signals"}
          </Button>
        </div>
      </div>

      {/* Instructions */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 space-y-3">
        <h2 className="text-sm font-semibold text-zinc-300">Setup Instructions</h2>

        <div className="space-y-2 text-xs text-zinc-400">
          <div>
            <h3 className="font-semibold text-zinc-300">Discord</h3>
            <ol className="ml-4 list-decimal space-y-1">
              <li>Go to your Discord server settings</li>
              <li>Navigate to Integrations → Webhooks</li>
              <li>Click &quot;New Webhook&quot; and copy the URL</li>
              <li>Paste the URL above and test</li>
            </ol>
          </div>

          <div>
            <h3 className="font-semibold text-zinc-300">Telegram</h3>
            <ol className="ml-4 list-decimal space-y-1">
              <li>Message @BotFather on Telegram to create a bot</li>
              <li>Get your bot token and your chat ID</li>
              <li>Use format: https://api.telegram.org/bot&lt;TOKEN&gt;/sendMessage?chat_id=&lt;CHAT_ID&gt;</li>
            </ol>
          </div>

          <div>
            <h3 className="font-semibold text-zinc-300">Slack</h3>
            <ol className="ml-4 list-decimal space-y-1">
              <li>Go to your Slack workspace settings</li>
              <li>Create an incoming webhook integration</li>
              <li>Copy the webhook URL and paste above</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
