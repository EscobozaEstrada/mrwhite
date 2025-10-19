import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Calendar } from "lucide-react";

interface CancelSubscriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  loading: boolean;
}

const CancelSubscriptionDialog: React.FC<CancelSubscriptionDialogProps> = ({
  open,
  onOpenChange,
  onConfirm,
  loading
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Cancel Subscription
          </DialogTitle>
          <div className="pt-2">
            <div className="mb-2">
              Are you sure you want to cancel your Elite Pack subscription?
            </div>
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-md p-3 text-sm">
              <div className="flex items-start gap-2">
                <Calendar className="h-4 w-4 text-yellow-500 mt-0.5" />
                <div>
                  <div className="font-medium text-yellow-400">Important:</div>
                  <div className="text-muted-foreground">
                    Your subscription will remain <span className="font-medium">active until the end of your current billing period</span>. 
                    You'll continue to have access to all Elite features until then.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DialogHeader>
        <DialogFooter className="flex flex-row justify-end gap-2 sm:justify-end">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Keep Subscription
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? "Canceling..." : "Yes, Cancel Subscription"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CancelSubscriptionDialog; 