import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Send } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button, GlassCard } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { api, post } from "@/services/api";
import type { Delivery } from "@/types/fleet";

interface SMSAcceptance {
  message_id: string;
  status: string;
}

export function DeliverySMSPage() {
  const { deliveryId = "" } = useParams();
  const [message, setMessage] = useState("");
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const delivery = useQuery({
    queryKey: ["delivery-sms", deliveryId],
    queryFn: () => api<Delivery>(`/deliveries/${deliveryId}`),
    enabled: Boolean(deliveryId),
  });
  const send = useMutation({
    mutationFn: () => post<SMSAcceptance>(`/deliveries/${deliveryId}/sms`, { message }),
  });

  return (
    <div className="max-w-3xl space-y-6">
      <Link to="/app/deliveries" className="inline-flex items-center gap-2 text-sm text-muted hover:text-ink">
        <ArrowLeft size={16} /> Back to deliveries
      </Link>
      <div>
        <h1 className="text-gradient text-3xl font-extrabold">Message delivery customer</h1>
        <p className="text-muted">Send a one-time SMS through the configured AfroMessage account.</p>
      </div>
      <GlassCard hover={false} className="space-y-4">
        {delivery.isLoading && <p className="text-sm text-muted">Loading delivery…</p>}
        {delivery.data && (
          <>
            <div className="rounded-xl border border-line bg-bg/50 p-3 text-sm">
              <p><span className="text-muted">Delivery:</span> {delivery.data.reference}</p>
              <p><span className="text-muted">Recipient:</span> {delivery.data.customer_name || "Customer"} · {delivery.data.customer_phone || "No phone number"}</p>
            </div>
            {delivery.data.customer_phone ? (
              <form className="space-y-4" onSubmit={(event) => {
                event.preventDefault();
                if (consentConfirmed) send.mutate();
              }}>
                <label className="block space-y-1 text-sm">
                  <span>Message</span>
                  <textarea
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    maxLength={1600}
                    rows={5}
                    required
                    className="focus-ring w-full rounded-xl border border-line bg-bg/60 px-3 py-2 text-ink"
                  />
                  <span className="text-xs text-muted">{message.length}/1600 characters. Message and provider fees may vary by segment.</span>
                </label>
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" checked={consentConfirmed} onChange={(event) => setConsentConfirmed(event.target.checked)} />
                  <span>I confirm this customer agreed to receive delivery updates and I want to send this SMS now.</span>
                </label>
                <Button type="submit" disabled={!message.trim() || !consentConfirmed || send.isPending}>
                  <Send size={16} />{send.isPending ? "Sending…" : "Send SMS now"}
                </Button>
              </form>
            ) : <p className="text-sm text-muted">Add a customer phone number to this delivery before sending an SMS.</p>}
          </>
        )}
        <FormError message={delivery.error?.message ?? send.error?.message} />
        {send.data && (
          <p role="status" className="rounded-xl border border-line bg-bg/50 p-3 text-sm">
            AfroMessage accepted the request. Provider status: {send.data.status}. Message ID: {send.data.message_id}.
            This confirms provider acceptance only, not delivery to the phone.
          </p>
        )}
      </GlassCard>
    </div>
  );
}
