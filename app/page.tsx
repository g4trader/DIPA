
import dynamic from "next/dynamic";
const DipaPanel = dynamic(() => import("@/components/DipaPanel"), { ssr: false });
export default function Page(){ return <DipaPanel/>; }
