import { ReactNode } from "react";

export default function Page({ title, description, action, children }: { title: string; description: string; action?: ReactNode; children: ReactNode }) {
  return <div className="content">
    <div className="page-head"><div><h1>{title}</h1><p className="subtle">{description}</p></div>{action}</div>
    {children}
  </div>;
}
