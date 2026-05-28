import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Settings2, Save, RotateCcw } from "lucide-react";
import {
  SOFT_CONSTRAINTS,
  defaultSoftConstraintWeights,
  type SoftConstraintWeights,
} from "@/lib/soft-constraints";

interface SettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  softWeights: SoftConstraintWeights;
  setSoftWeights: (val: SoftConstraintWeights) => void;
}

export default function SettingsModal({
  open,
  onOpenChange,
  softWeights,
  setSoftWeights,
}: SettingsModalProps) {
  const updateWeight = (configKey: keyof SoftConstraintWeights, raw: string) => {
    const parsed = parseFloat(raw);
    setSoftWeights({
      ...softWeights,
      [configKey]: Number.isFinite(parsed) ? parsed : 0,
    });
  };

  const resetDefaults = () => setSoftWeights(defaultSoftConstraintWeights());

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
              <Settings2 size={18} className="text-slate-600" />
            </div>
            <DialogTitle className="text-xl">Hệ số ràng buộc mềm</DialogTitle>
          </div>
          <DialogDescription>
            8 hệ số phạt benchmark (RB4–RB11). Giá trị ghi đè khi chạy solver và tính biểu đồ phân phối.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-widest text-slate-400">
              Soft Constraint Weights
            </h4>
            <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={resetDefaults}>
              <RotateCcw size={12} /> Mặc định
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {SOFT_CONSTRAINTS.map((constraint) => (
              <div key={constraint.key} className="space-y-1.5">
                <Label className="text-xs font-semibold text-slate-700" title={constraint.description}>
                  {constraint.label}
                </Label>
                <Input
                  type="number"
                  step="any"
                  min={0}
                  value={softWeights[constraint.configKey]}
                  onChange={(e) => updateWeight(constraint.configKey, e.target.value)}
                  className="h-9"
                />
                <p className="text-[10px] text-slate-400">{constraint.benchmarkKey}</p>
              </div>
            ))}
          </div>

          <Separator />

          <div className="bg-amber-50 rounded-lg p-3 border border-amber-100 flex gap-3 text-amber-800">
            <div className="shrink-0 pt-0.5">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse mt-1" />
            </div>
            <p className="text-[11px] leading-relaxed font-medium">
              Hệ số cao hơn = tiêu chí quan trọng hơn trong điểm phạt tổng. Thay đổi lớn có thể làm solver lâu hơn hoặc khó tìm nghiệm khả thi.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Hủy</Button>
          <Button className="bg-blue-600 hover:bg-blue-700 gap-2" onClick={() => onOpenChange(false)}>
            <Save size={14} /> Lưu cấu hình
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
