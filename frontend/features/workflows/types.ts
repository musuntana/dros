import type {
  GateEvaluationRead,
  WorkflowDetailResponse,
  WorkflowInstanceRead,
  WorkflowTaskRead,
} from "@/lib/api/generated/control-plane";

export interface WorkflowSnapshotOption {
  datasetId: string;
  datasetName: string;
  deidStatus: string;
  phiScanStatus: string;
  snapshotId: string;
  snapshotNo: number;
}

export interface WorkflowDetailViewModel {
  gateEvaluations: GateEvaluationRead[];
  tasks: WorkflowTaskRead[];
  workflow: WorkflowInstanceRead;
}

export function toWorkflowDetailViewModel(detail: WorkflowDetailResponse): WorkflowDetailViewModel {
  return {
    gateEvaluations: detail.gate_evaluations ?? [],
    tasks: detail.tasks ?? [],
    workflow: detail.workflow,
  };
}
