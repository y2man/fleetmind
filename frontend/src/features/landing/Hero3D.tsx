import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Mesh } from "three";

function Globe() {
  const ref = useRef<Mesh>(null);
  useFrame((_, d) => { if (ref.current) { ref.current.rotation.y += d * 0.3; ref.current.rotation.x += d * 0.08; } });
  return <mesh ref={ref}><icosahedronGeometry args={[1.7, 1]} /><meshBasicMaterial color="#4d8dff" wireframe /></mesh>;
}
export default function Hero3D() {
  return <Canvas camera={{ position: [0, 0, 5] }} dpr={[1, 1.5]}><Globe /></Canvas>;
}
