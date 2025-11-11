"use client";
import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { ArrowRight, Sparkles, Loader2 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, BarChart, Bar, Legend, CartesianGrid } from "recharts";

type Seller = { id: string; name: string; region: string; city: string; monthlyTarget: number };
type Product = { id: string; sku: string; name: string; brand: string; category: string; promo: boolean };
type Sale = { id: string; date: string; orderId: string; sellerId: string; clientId: string; region: string; city: string; productId: string; qty: number; unitPrice: number; discount: number };

const REGIONS = ["Porto Alegre","Grande Porto Alegre","Vale dos Sinos","Serra Gaúcha","Litoral Norte","Região Carbonífera"] as const;
const BRANDS = ["Nissin","Red Bull","AB Mauri","Mars","Ypê","Hemmer","Marilan","Ajinomoto","Condor"] as const;

function seededRandom(seed:number){return function(){seed=(seed*9301+49297)%233280;return seed/233280;}}
function genData(){
  const rnd=seededRandom(202510);
  const sellers:Seller[]=Array.from({length:24}).map((_,i)=>({id:`S${i+1}`, name:`Vendedor ${String.fromCharCode(65+(i%26))}${i+1}`, region:REGIONS[Math.floor(rnd()*REGIONS.length)], city:"—", monthlyTarget:Math.round(150000+rnd()*300000)}));
  const categories=["Massas instantâneas","Bebidas energéticas","Panificação e confeitaria","Confeitos e petcare","Limpeza doméstica","Condimentos e conservas","Biscoitos e snacks","Temperos e caldos","Utensílios de limpeza"];
  const products:Product[]=Array.from({length:180}).map((_,i)=>{const b=BRANDS[Math.floor(rnd()*BRANDS.length)], c=categories[Math.floor(rnd()*categories.length)]; return {id:`P${i+1}`, sku:`${b.slice(0,3).toUpperCase()}-${1000+i}`, name:`${b} ${c.split(" ")[0]} ${i+1}`, brand:b, category:c, promo:rnd()<0.25};});
  const clients=Array.from({length:400}).map((_,i)=>({id:`C${i+1}`, name:`Cliente ${i+1}`, region:REGIONS[Math.floor(rnd()*REGIONS.length)], city:"—"}));
  const months=["2025-09","2025-10","2025-11"]; const sales:Sale[]=[]; let oid=1;
  for(const m of months){for(let r=0;r<8000;r++){const s=sellers[Math.floor(rnd()*sellers.length)], c=clients[Math.floor(rnd()*clients.length)], p=products[Math.floor(rnd()*products.length)]; const day=1+Math.floor(rnd()*30), qty=1+Math.floor(rnd()*12), price=8+rnd()*70, disc=[0,0.03,0.05,0.1][Math.floor(rnd()*4)]; sales.push({id:`L${m}-${r}`, date:`${m}-${String(day).padStart(2,"0")}T10:00:00`, orderId:`O${oid++}`, sellerId:s.id, clientId:c.id, region:c.region, city:"—", productId:p.id, qty, unitPrice:Math.round(price*100)/100, discount:disc});}}
  return {sellers, products, clients, sales} as const;
}
const DATA=genData();
type QueryResult={kpis?:{label:string;value:string}[]; narrative?:string};
function currency(n:number){return n.toLocaleString("pt-BR",{style:"currency",currency:"BRL"});}
function monthKey(d:string){return d.slice(0,7);}
function aggregateSales(month?:string){return DATA.sales.filter(s=>!month || monthKey(s.date)===month);}
function runQuery(q:string):QueryResult{const m=(/2025-(09|10|11)/.exec(q)?.[0])||"2025-11"; const rows=aggregateSales(m); const rev=rows.reduce((a,r)=>a+r.qty*r.unitPrice*(1-r.discount),0); const units=rows.reduce((a,r)=>a+r.qty,0); return {kpis:[{label:"Receita",value:currency(rev)},{label:"Unidades",value:units.toLocaleString("pt-BR")}], narrative:`Resumo do mês ${m}.`};}

export default function DipaPanel(){
  const [question,setQuestion]=useState("Mostre o comparativo de meta vs realizado de 2025-11 por região e vendedor");
  const [answers,setAnswers]=useState<{role:"user"|"assistant";text:string;result?:QueryResult}[]>([]);
  const [busy,setBusy]=useState(false); const [month,setMonth]=useState("2025-11");
  const ask=async(q:string)=>{setBusy(true); setAnswers(a=>[...a,{role:"user",text:q}]); const result=runQuery(q); setAnswers(a=>[...a,{role:"assistant",text:result.narrative||"",result}]); setBusy(false);};
  useEffect(()=>{ if(answers.length===0) ask(question); },[]);
  return (<div className="p-6 max-w-5xl mx-auto">
    <h1 className="text-2xl font-semibold mb-3">DIPA – Dipam Intelligence & Performance Assistant</h1>
    <div className="flex gap-2"><input className="border rounded px-3 py-2 flex-1" value={question} onChange={e=>setQuestion(e.target.value)} /><button className="border rounded px-3" onClick={()=>ask(question)}>{busy?"...":"Perguntar"}</button></div>
    <div className="mt-4">{answers.map((m,i)=>(<div key={i} className="py-2">{m.role==="user"?"Você: ":"DIPA: "}{m.text}</div>))}</div>
  </div>);
}
