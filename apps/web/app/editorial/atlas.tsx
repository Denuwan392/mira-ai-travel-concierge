"use client";

import { Component, useState, type ReactNode } from "react";
import { Canvas } from "@react-three/fiber";
import { Environment, Lightformer } from "@react-three/drei";

class SceneBoundary extends Component<{children:ReactNode; failed:()=>void},{error:boolean}> {
  state={error:false};
  static getDerivedStateFromError(){return {error:true}}
  componentDidCatch(){this.props.failed()}
  render(){return this.state.error ? null : this.props.children}
}
export default function Atlas({selected,count,select,failed}:{selected:number;count:number;select:(i:number)=>void;failed:()=>void}){
  const [tilt,setTilt]=useState(0);
  return <div className="atlas-scene" aria-hidden="true" onPointerMove={e=>{const box=e.currentTarget.getBoundingClientRect();setTilt(((e.clientX-box.left)/box.width-.5)*.14)}} onPointerLeave={()=>setTilt(0)}>
    <SceneBoundary failed={failed}><Canvas frameloop="demand" dpr={1} camera={{position:[0,0,4.4],fov:40}}>
      <ambientLight intensity={1.4}/><directionalLight position={[2,4,3]} intensity={3}/>
      <Environment resolution={32} frames={1}><Lightformer intensity={3} position={[0,2,2]} scale={[4,2,1]}/></Environment>
      <group rotation={[-.3,tilt,.06]}>
        <mesh><torusGeometry args={[1,.055,8,72]}/><meshStandardMaterial color="#d4b687" metalness={.65} roughness={.28}/></mesh>
        <mesh position={[0,0,-.09]}><circleGeometry args={[.98,64]}/><meshStandardMaterial color="#183b30"/></mesh>
        {Array.from({length:count},(_,i)=>{const a=i*Math.PI*2/count;return <mesh key={i} position={[Math.sin(a)*.83,Math.cos(a)*.83,.07]} onClick={()=>select(i)}><sphereGeometry args={[.11,12,8]}/><meshStandardMaterial color={i===selected?"#f26b1d":"#c5a778"}/></mesh>})}
        <group rotation={[0,0,-selected*Math.PI*2/count]}><mesh position={[0,.3,.08]}><coneGeometry args={[.15,.65,4]}/><meshStandardMaterial color="#f26b1d"/></mesh><mesh position={[0,-.3,.08]} rotation={[0,0,Math.PI]}><coneGeometry args={[.15,.65,4]}/><meshStandardMaterial color="#e9dec3"/></mesh></group>
      </group>
    </Canvas></SceneBoundary>
  </div>
}
