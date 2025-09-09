/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Item, Question, NextResponse } from "@/types/form";
import {
  getPrimeraPregunta,
  getQuestionById,
  guardarYAvanzar,
  verificarImagen,
  finalizarSubmission,
  createSubmission, // ✅ crear submission al iniciar
} from "@/lib/api";
import { isOcr, isImageOnly, today } from "@/lib/ui";

type ActorMini = { id: string; nombre: string; documento?: string | null };
const SUB_KEY = (qid: string) => `submission:${qid}`;

const tagOf = (q: Question) => String((q as any)?.semantic_tag || "none").toLowerCase();
const isActorTag = (t: string) => t === "proveedor" || t === "transportista" || t === "receptor";

const valueFromOCR = (resp: any, tag: string) => {
  if (!resp) return "";
  if (tag === "placa" && resp.placa) return resp.placa as string;
  if (tag === "contenedor" && resp.contenedor) return resp.contenedor as string;
  if (tag === "precinto" && resp.precinto) return resp.precinto as string;
  return (resp.ocr_raw as string) || "";
};

function fdSet(fd: FormData, k: string, v: any) {
  if (v === undefined || v === null) return;
  fd.set(k, typeof v === "string" || v instanceof Blob ? v : String(v));
}

export function useFormFlow(
  questionnaire_id?: string | null,
  submission_id?: string | null
) {
  const qid = questionnaire_id ?? "";

  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [mostrarResumen, setMostrarResumen] = useState(false);
  const [finalizado, setFinalizado] = useState(false);

  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Para evitar TS con el prop del child, dejamos el tipo que más encaja
  const lastRef = useRef<HTMLDivElement | null>(null);
  const inFlight = useRef(false);

  // Bootstrap: crear/recuperar submission y cargar primera pregunta
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError(null);
        setLoading(true);
        if (!qid) { setLoading(false); return; }

        // 1) recuperar/propagar submission_id
        let sid: string | null = submission_id ?? null;
        if (!sid) {
          try { sid = sessionStorage.getItem(`submission:${qid}`); } catch {}
        }

        // 2) si no existe, crearla ENVIANDO questionnaire
        if (!sid) {
          const created: any = await createSubmission({
            questionnaire: qid,
            tipo_fase: "entrada",
          });
          sid = created?.id || created?.uuid || created?.pk || null;
          if (!sid) throw new Error("El backend no devolvió ID de submission.");
          try { sessionStorage.setItem(`submission:${qid}`, sid); } catch {}
        }

        if (cancelled) return;
        setSubmissionId(sid);

        // 3) cargar la primera pregunta
        const first = await getPrimeraPregunta(qid);
        if (cancelled) return;
        setItems([{
          q: first,
          value: first.type === "date" ? today() : "",
          saved: false,
          editing: true,
          autoSubmitted: first.type === "date" ? false : undefined,
        }]);
      } catch (e: any) {
        setError(e?.message || "Error inicializando el formulario");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [qid, submission_id]);

  // Scroll al último ítem
  useEffect(() => {
    lastRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [items.length]);

  // Autoguarda fecha “hoy” cuando corresponda
  useEffect(() => {
    const idx = items.length - 1;
    const it = items[idx];
    if (!it?.editing || it.q.type !== "date" || it.autoSubmitted) return;
    submitOne(idx, it.value || today());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.map(i => `${i.q.id}:${i.value}:${i.autoSubmitted}`).join("|")]);

  async function submitOne(index: number, valueOverride?: string, actorOverride?: ActorMini) {
    const it = items[index] as any;
    if (!it?.editing) return;

    if (!submissionId) {
      setError("Falta 'submission_id'.");
      return;
    }
    if (inFlight.current) return;

    inFlight.current = true;
    setSending(true);

    try {
      const q = it.q as Question;
      const tag = tagOf(q);

      // Validaciones básicas por tipo
      if (isActorTag(tag)) {
        const actor = actorOverride ?? it.actor;
        if (!actor?.id) throw new Error("Selecciona un actor válido.");
      } else if (q.type === "file") {
        const files: File[] = it.files || [];
        if (isOcr(q)) {
          if (files.length !== 1) throw new Error("Adjunta exactamente 1 imagen.");
        } else if (isImageOnly(q)) {
          if (files.length < 1) throw new Error("Adjunta al menos 1 imagen.");
        }
      } else if (q.required) {
        const v = valueOverride ?? (it.value as string);
        const ok = q.type === "choice" ? !!v : (v || "").trim().length > 0;
        if (!ok) throw new Error("Falta completar el campo.");
      }

      // FormData para /guardar_avanzar/
      const fd = new FormData();
      fdSet(fd, "submission_id", submissionId);
      fdSet(fd, "question_id", q.id);
      fdSet(fd, "force_truncate_future", "1");

      let savedValue = "";

      const actor = actorOverride ?? it.actor;
      if (isActorTag(tag) && actor?.id) {
        fdSet(fd, "actor_id", actor.id);
        fdSet(fd, "answer_text", actor.nombre || "");
        savedValue = actor.nombre || "";
      } else if (q.type === "choice") {
        const v = valueOverride ?? (it.value as string);
        fdSet(fd, "answer_choice_id", v);
        savedValue = v;
      } else if (q.type === "file") {
        const files: File[] = it.files || [];
        if (files[0]) fdSet(fd, "answer_file", files[0]);
        if (isOcr(q)) {
          const v = valueOverride ?? (it.value as string) || "";
          fdSet(fd, "answer_text", v);
          savedValue = v;
        } else {
          savedValue = String(files.length || 0);
        }
      } else {
        const v = valueOverride ?? (q.type === "date" && !it.value ? today() : (it.value as string));
        fdSet(fd, "answer_text", v);
        savedValue = v;
      }

      const resp = (await guardarYAvanzar(fd)) as NextResponse & {
        is_finished?: boolean;
        next_question?: Question | null;
        next_question_id?: string | null;
        mensaje?: string;
      };

      let finished = typeof resp?.is_finished === "boolean" ? resp.is_finished : false;
      if (!finished && resp?.mensaje) finished = /finalizad/i.test(String(resp.mensaje));

      // resolver siguiente pregunta
      let nextQ: Question | null = null;
      if ((resp as any)?.next_question) nextQ = (resp as any).next_question as Question;
      else if ((resp as any)?.next_question_id) {
        try { nextQ = await getQuestionById((resp as any).next_question_id as string); } catch {}
      } else if ((resp as any)?.id && (resp as any)?.text) {
        nextQ = resp as unknown as Question;
      }

      setItems(prev => {
        const copy = [...prev];
        copy[index] = {
          ...(copy[index] as any),
          saved: true,
          editing: false,
          value: savedValue,
          autoSubmitted: true,
          autoFromOCR: false,
          valueFromOCR: undefined,
        };
        let out = copy.slice(0, index + 1);
        if (finished) { setMostrarResumen(true); return out; }
        if (nextQ) {
          out = [
            ...out,
            {
              q: nextQ,
              value: nextQ.type === "date" ? today() : "",
              saved: false,
              editing: true,
              autoSubmitted: nextQ.type === "date" ? false : undefined,
            } as Item,
          ];
        }
        return out;
      });
    } catch (e: any) {
      setError(e?.message || "Error guardando la respuesta");
    } finally {
      inFlight.current = false;
      setSending(false);
    }
  }

  function setVal(i: number, v: string) {
    setItems(prev => {
      const copy = [...prev];
      const cur: any = copy[i];
      if (!cur) return copy;
      copy[i] = { ...cur, value: v, saved: false, editing: true, autoFromOCR: false };
      return copy;
    });
  }

  function setActor(i: number, actor: ActorMini) {
    setItems(prev => {
      const copy = [...prev];
      const cur: any = copy[i];
      if (!cur) return copy;
      copy[i] = { ...cur, actor, value: actor?.nombre || "", saved: false, editing: true, autoFromOCR: false };
      return copy;
    });
  }

  function onSelectChoice(i: number, id: string) {
    setVal(i, id);
    submitOne(i, id);
  }

  function onEnter(e: React.KeyboardEvent, i: number) {
    if (e.key === "Enter") {
      e.preventDefault();
      submitOne(i);
    }
  }

  function removeFile(i: number, k: number) {
    setItems(prev => {
      const copy = [...prev];
      const it: any = copy[i];
      const files: File[] = [...(it?.files || [])];
      const previews: string[] = [...(it?.previews || [])];
      const url = previews[k];
      files.splice(k, 1);
      previews.splice(k, 1);
      if (url) { try { URL.revokeObjectURL(url); } catch {} }
      copy[i] = { ...it, files, previews, saved: false, editing: true, autoFromOCR: false };
      return copy;
    });
  }

  async function onFilesChange(i: number, list: FileList | null) {
    if (!list?.length) return;
    const q = items[i]?.q;
    const incoming = Array.from(list);
    const file = incoming[0];

    setItems(prev => {
      const copy = [...prev];
      const it: any = copy[i];
      if (!q) return copy;

      if (isImageOnly(q)) {
        const curFiles: File[] = it.files || [];
        const curPreviews: string[] = it.previews || [];
        const room = Math.max(0, 2 - curFiles.length);
        const toAdd = incoming.slice(0, room);
        copy[i] = {
          ...it,
          files: [...curFiles, ...toAdd],
          previews: [...curPreviews, ...toAdd.map(f => URL.createObjectURL(f))],
          saved: false,
          editing: true,
          autoFromOCR: false,
        };
        return copy;
      }

      if (isOcr(q)) {
        (it.previews || []).forEach((u: string) => { try { URL.revokeObjectURL(u); } catch {} });
        copy[i] = {
          ...it,
          files: [file],
          previews: [URL.createObjectURL(file)],
          ocr: "Procesando...",
          value: "",
          saved: false,
          editing: true,
          autoFromOCR: false,
        };
      }
      return copy;
    });

    if (q && isOcr(q)) {
      try {
        const mode = (q as any)?.file_mode === "ocr_only" ? "document" : "text";
        const data: any = await verificarImagen({ question_id: q.id, imagen: file, mode });
        const tag = tagOf(q);
        const nextValue = valueFromOCR(data, tag);
        setItems(prev => {
          const copy = [...prev];
          const it: any = copy[i];
          if (!it) return copy;
          copy[i] = {
            ...it,
            ocr: data,
            value: nextValue,
            valueFromOCR: nextValue,
            autoFromOCR: true,
            saved: false,
            editing: true,
          };
          return copy;
        });
      } catch {
        setItems(prev => {
          const copy = [...prev];
          const it: any = copy[i];
          if (!it) return copy;
          copy[i] = { ...it, ocr: "Error en la verificación", value: "", saved: false, editing: true, autoFromOCR: false };
          return copy;
        });
      }
    }
  }

  async function retryOCR(i: number) {
    const it: any = items[i];
    const q = it?.q as Question | undefined;
    const file: File | undefined = it?.files?.[0];
    if (!q || !file || !isOcr(q)) return;

    setItems(prev => {
      const copy = [...prev];
      copy[i] = { ...(copy[i] as any), ocr: "Procesando...", value: "", saved: false, editing: true, autoFromOCR: false };
      return copy;
    });

    try {
      const mode = (q as any)?.file_mode === "ocr_only" ? "document" : "text";
      const data: any = await verificarImagen({ question_id: q.id, imagen: file, mode });
      const tag = tagOf(q);
      const nextValue = valueFromOCR(data, tag);
      setItems(prev => {
        const copy = [...prev];
        copy[i] = {
          ...(copy[i] as any),
          ocr: data,
          value: nextValue,
          valueFromOCR: nextValue,
          autoFromOCR: true,
          saved: false,
          editing: true,
        };
        return copy;
      });
    } catch {
      setItems(prev => {
        const copy = [...prev];
        copy[i] = { ...(copy[i] as any), ocr: "Error en la verificación", value: "", saved: false, editing: true, autoFromOCR: false };
        return copy;
      });
    }
  }

  async function onEnviar() {
    if (!submissionId) {
      setError("Falta 'submission_id'.");
      return;
    }
    try {
      setSending(true);
      await finalizarSubmission(submissionId);
      setFinalizado(true);
      try { if (qid) sessionStorage.removeItem(SUB_KEY(qid)); } catch {}
    } catch (e: any) {
      setError(e?.message || "No se pudo enviar el formulario");
    } finally {
      setSending(false);
    }
  }

  const total = items.length;
  const respondidas = useMemo(() => items.filter(i => i.saved).length, [items]);

  return {
    submissionId, items, setItems,
    mostrarResumen, setMostrarResumen,
    finalizado, loading, sending, error,
    lastRef,

    isOcr, isImageOnly, today,
    choiceText: (it: Item) => it.q.choices?.find(c => c.id === it.value)?.text || "",
    answerPreview: (it: Item) => {
      if (it.q.type === "choice") return it.q.choices?.find(c => c.id === it.value)?.text || "";
      if (it.q.type === "file") {
        if (isOcr(it.q)) return (it.value as string) || "(sin texto)";
        const n = (it as any).files?.length || 0;
        return n === 0 ? "(sin imagen)" : `${n} imagen${n > 1 ? "es" : ""}`;
      }
      return (it.value as string) || "(vacío)";
    },

    submitOne, setVal, setActor, onSelectChoice, onEnter,
    onFilesChange, removeFile, onEnviar, retryOCR,

    total, respondidas,
  };
}
